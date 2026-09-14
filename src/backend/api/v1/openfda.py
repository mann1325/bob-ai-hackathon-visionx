import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import Settings
from app.dependencies import get_app_settings
from schemas.openfda import OpenFDADrugSearchResponse, OpenFDAEventSearchResponse
from services.openfda_client import (
    OpenFDAAPIError,
    OpenFDAAuthError,
    OpenFDAClient,
    OpenFDAClientError,
    OpenFDATimeoutError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openfda", tags=["openfda"])


def get_openfda_client(settings: Settings = Depends(get_app_settings)) -> OpenFDAClient:
    return OpenFDAClient(
        base_url=settings.openfda_api_base_url,
        api_key=settings.openfda_api_key,
    )


@router.get(
    "/drugs/search",
    response_model=OpenFDADrugSearchResponse,
    summary="Auxiliary live drug lookup via openFDA drug label API",
)
def search_openfda_drugs(
    q: str = Query(..., min_length=1, description="Drug name (brand or generic) to query"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    client: OpenFDAClient = Depends(get_openfda_client),
) -> OpenFDADrugSearchResponse:
    """
    Perform an auxiliary drug label search against the public openFDA API.
    Data returned is for reference/exploration and is distinct from SignalTrace pipeline data.
    """
    try:
        return client.search_drugs(query=q, limit=limit)
    except OpenFDATimeoutError as exc:
        logger.warning("openFDA timeout for drug query '%s'", q)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The openFDA service timed out while processing the drug query.",
        ) from exc
    except OpenFDAAuthError as exc:
        logger.error("openFDA auth error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication failed with openFDA service.",
        ) from exc
    except OpenFDAAPIError as exc:
        logger.error("openFDA upstream error for drug query '%s': %s", q, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve data from openFDA upstream service.",
        ) from exc
    except OpenFDAClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error querying openFDA drugs: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while querying openFDA.",
        ) from exc


@router.get(
    "/events/search",
    response_model=OpenFDAEventSearchResponse,
    summary="Auxiliary live adverse event search via openFDA event API",
)
def search_openfda_events(
    drug: Optional[str] = Query(None, description="Medicinal product / drug name"),
    event: Optional[str] = Query(None, description="Adverse reaction / MedDRA PT"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    client: OpenFDAClient = Depends(get_openfda_client),
) -> OpenFDAEventSearchResponse:
    """
    Perform an auxiliary adverse event search against the public openFDA event API.
    Data returned is for reference/exploration and is distinct from SignalTrace pipeline data.
    """
    if not drug and not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'drug' or 'event' query parameters must be specified.",
        )

    try:
        return client.search_events(drug=drug, event=event, limit=limit)
    except OpenFDATimeoutError as exc:
        logger.warning("openFDA timeout for event query drug='%s' event='%s'", drug, event)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The openFDA service timed out while processing the event query.",
        ) from exc
    except OpenFDAAuthError as exc:
        logger.error("openFDA auth error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication failed with openFDA service.",
        ) from exc
    except OpenFDAAPIError as exc:
        logger.error("openFDA upstream error for event query: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve data from openFDA upstream service.",
        ) from exc
    except OpenFDAClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error querying openFDA events: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while querying openFDA.",
        ) from exc
