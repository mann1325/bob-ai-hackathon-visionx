import logging
import time
from typing import Any, Dict, List, Optional
import httpx

from schemas.openfda import (
    OpenFDADrugItem,
    OpenFDADrugSearchResponse,
    OpenFDAEventItem,
    OpenFDAEventSearchResponse,
)

logger = logging.getLogger(__name__)


class OpenFDAClientError(Exception):
    """Base exception for openFDA client errors."""
    pass


class OpenFDAAuthError(OpenFDAClientError):
    """Raised when authentication with openFDA fails (e.g. invalid API key)."""
    pass


class OpenFDATimeoutError(OpenFDAClientError):
    """Raised when request to openFDA times out."""
    pass


class OpenFDAAPIError(OpenFDAClientError):
    """Raised when openFDA returns an upstream server error."""
    pass


class OpenFDAClient:
    """
    Client for openFDA REST API providing auxiliary, on-demand reference lookups.
    Does not calculate or alter SignalTrace PRR/ROR signal metrics.
    """

    def __init__(
        self,
        base_url: str = "https://api.fda.gov",
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if (api_key and api_key.strip() and api_key != "your_openfda_key") else None
        self.timeout = timeout
        self.max_retries = max_retries

    def _build_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Attach optional API key if configured."""
        result = dict(params)
        if self.api_key:
            result["api_key"] = self.api_key
        return result

    def _execute_get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute an HTTP GET request against openFDA with bounded retries on transient 5xx/network failures.
        Returns parsed JSON dict, or None if upstream returns 404 (no matches).
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        final_params = self._build_params(params)

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params=final_params)

                if response.status_code == 404:
                    # openFDA returns 404 with {"error": {"code": "NOT_FOUND"}} when search has 0 results
                    return None

                if response.status_code in (401, 403):
                    logger.warning("openFDA authentication error HTTP %s", response.status_code)
                    raise OpenFDAAuthError("openFDA API authentication failed. Check OPENFDA_API_KEY.")

                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(0.5 * (2 ** attempt))
                        continue
                    raise OpenFDAAPIError(f"openFDA upstream server error HTTP {response.status_code}")

                if response.status_code >= 400:
                    raise OpenFDAClientError(f"openFDA client error HTTP {response.status_code}: {response.text[:200]}")

                try:
                    return response.json()
                except Exception as exc:
                    logger.error("Failed to parse JSON from openFDA response")
                    raise OpenFDAAPIError("Malformed JSON received from openFDA.") from exc

            except (httpx.TimeoutException, httpx.ConnectTimeout) as exc:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                logger.warning("openFDA request timed out after %s retries", self.max_retries)
                raise OpenFDATimeoutError("openFDA service request timed out.") from exc
            except (httpx.NetworkError, httpx.ConnectError) as exc:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                logger.warning("openFDA network error: %s", type(exc).__name__)
                raise OpenFDAAPIError("Network error connecting to openFDA service.") from exc
            except (OpenFDAAuthError, OpenFDAAPIError, OpenFDAClientError, OpenFDATimeoutError):
                raise
            except Exception as exc:
                logger.error("Unexpected error during openFDA request: %s", type(exc).__name__)
                raise OpenFDAAPIError(f"Unexpected error communicating with openFDA: {exc}") from exc

        return None

    def search_drugs(self, query: str, limit: int = 10) -> OpenFDADrugSearchResponse:
        """
        Quick auxiliary lookup against openFDA drug labels (`/drug/label.json`).
        """
        clean_query = query.strip().replace('"', "")
        if not clean_query:
            return OpenFDADrugSearchResponse(query=query, total=0, results=[])

        search_expr = f'openfda.brand_name:"{clean_query}"+openfda.generic_name:"{clean_query}"'
        params = {"search": search_expr, "limit": min(limit, 50)}

        raw_data = self._execute_get("/drug/label.json", params)
        if not raw_data or "results" not in raw_data:
            return OpenFDADrugSearchResponse(query=query, total=0, results=[])

        total = raw_data.get("meta", {}).get("results", {}).get("total", len(raw_data["results"]))
        items: List[OpenFDADrugItem] = []

        for r in raw_data.get("results", []):
            openfda_block = r.get("openfda", {})
            purpose_list = r.get("purpose", [])
            warnings_list = r.get("warnings", [])

            items.append(
                OpenFDADrugItem(
                    brand_name=openfda_block.get("brand_name", []),
                    generic_name=openfda_block.get("generic_name", []),
                    manufacturer_name=openfda_block.get("manufacturer_name", []),
                    product_type=(
                        openfda_block.get("product_type", [None])[0]
                        if openfda_block.get("product_type")
                        else None
                    ),
                    route=openfda_block.get("route", []),
                    substance_name=openfda_block.get("substance_name", []),
                    purpose=purpose_list[0] if purpose_list else None,
                    warnings=warnings_list[0][:500] if warnings_list else None,
                )
            )

        return OpenFDADrugSearchResponse(query=query, total=total, results=items)

    def search_events(
        self,
        drug: Optional[str] = None,
        event: Optional[str] = None,
        limit: int = 10,
    ) -> OpenFDAEventSearchResponse:
        """
        Auxiliary lookup against openFDA adverse events (`/drug/event.json`).
        """
        clauses = []
        if drug and drug.strip():
            clean_drug = drug.strip().replace('"', "")
            clauses.append(f'patient.drug.medicinalproduct:"{clean_drug}"')
        if event and event.strip():
            clean_event = event.strip().replace('"', "")
            clauses.append(f'patient.reaction.reactionmeddrapt:"{clean_event}"')

        if not clauses:
            return OpenFDAEventSearchResponse(drug=drug, event=event, total=0, results=[])

        search_expr = "+AND+".join(clauses)
        params = {"search": search_expr, "limit": min(limit, 50)}

        raw_data = self._execute_get("/drug/event.json", params)
        if not raw_data or "results" not in raw_data:
            return OpenFDAEventSearchResponse(drug=drug, event=event, total=0, results=[])

        total = raw_data.get("meta", {}).get("results", {}).get("total", len(raw_data["results"]))
        items: List[OpenFDAEventItem] = []

        for r in raw_data.get("results", []):
            patient = r.get("patient", {})
            drugs_list = [
                d.get("medicinalproduct", "UNKNOWN")
                for d in patient.get("drug", [])
                if d.get("medicinalproduct")
            ]
            reactions_list = [
                reac.get("reactionmeddrapt", "UNKNOWN")
                for reac in patient.get("reaction", [])
                if reac.get("reactionmeddrapt")
            ]

            items.append(
                OpenFDAEventItem(
                    safetyreportid=str(r.get("safetyreportid", "")),
                    receivedate=str(r.get("receivedate", "")),
                    serious=str(r.get("serious", "")),
                    seriousnessdeath=str(r.get("seriousnessdeath", "")),
                    patient_age=str(patient.get("patientonsetage", "")),
                    patient_sex=str(patient.get("patientsex", "")),
                    drugs=drugs_list,
                    reactions=reactions_list,
                )
            )

        return OpenFDAEventSearchResponse(
            drug=drug,
            event=event,
            total=total,
            results=items,
        )
