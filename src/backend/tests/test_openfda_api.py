import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_app_settings
from schemas.openfda import (
    OpenFDADrugItem,
    OpenFDADrugSearchResponse,
    OpenFDAEventItem,
    OpenFDAEventSearchResponse,
)
from services.openfda_client import (
    OpenFDAAPIError,
    OpenFDAAuthError,
    OpenFDAClient,
    OpenFDAClientError,
    OpenFDATimeoutError,
)


def sample_openfda_drug_payload():
    return {
        "meta": {
            "disclaimer": "Do not rely on openFDA to make decisions regarding medical care.",
            "results": {"skip": 0, "limit": 1, "total": 1},
        },
        "results": [
            {
                "openfda": {
                    "brand_name": ["ASPIRIN 81MG"],
                    "generic_name": ["ASPIRIN"],
                    "manufacturer_name": ["Bayer HealthCare LLC"],
                    "product_type": ["HUMAN OTC DRUG"],
                    "route": ["ORAL"],
                    "substance_name": ["ASPIRIN"],
                },
                "purpose": ["Pain reliever/fever reducer"],
                "warnings": ["Reye's syndrome: Children and teenagers who have or are recovering from chicken pox..."],
            }
        ],
    }


def sample_openfda_event_payload():
    return {
        "meta": {
            "disclaimer": "Do not rely on openFDA to make decisions regarding medical care.",
            "results": {"skip": 0, "limit": 1, "total": 45},
        },
        "results": [
            {
                "safetyreportid": "10023481",
                "receivedate": "20240210",
                "serious": "1",
                "seriousnessdeath": "0",
                "patient": {
                    "patientonsetage": "68",
                    "patientsex": "1",
                    "drug": [{"medicinalproduct": "ASPIRIN"}],
                    "reaction": [{"reactionmeddrapt": "GASTROINTESTINAL BLEEDING"}],
                },
            }
        ],
    }


def test_openfda_drug_search_success(client: TestClient):
    """Test successful auxiliary openFDA drug lookup."""
    mock_resp = OpenFDADrugSearchResponse(
        query="aspirin",
        total=1,
        results=[
            OpenFDADrugItem(
                brand_name=["ASPIRIN 81MG"],
                generic_name=["ASPIRIN"],
                manufacturer_name=["Bayer HealthCare LLC"],
                product_type="HUMAN OTC DRUG",
                route=["ORAL"],
                substance_name=["ASPIRIN"],
                purpose="Pain reliever/fever reducer",
                warnings="Reye's syndrome: Children and teenagers...",
            )
        ],
    )

    with patch.object(OpenFDAClient, "search_drugs", return_value=mock_resp):
        response = client.get("/api/v1/openfda/drugs/search?q=aspirin")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "aspirin"
    assert data["total"] == 1
    assert data["source"] == "openFDA"
    assert data["is_auxiliary_lookup"] is True
    assert len(data["results"]) == 1
    assert data["results"][0]["brand_name"] == ["ASPIRIN 81MG"]
    assert data["results"][0]["generic_name"] == ["ASPIRIN"]
    assert "disclaimer" in data


def test_openfda_drug_search_empty_results(client: TestClient):
    """Test openFDA returning 0 results."""
    mock_resp = OpenFDADrugSearchResponse(query="nonexistent123", total=0, results=[])

    with patch.object(OpenFDAClient, "search_drugs", return_value=mock_resp):
        response = client.get("/api/v1/openfda/drugs/search?q=nonexistent123")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["results"] == []


def test_openfda_event_search_success(client: TestClient):
    """Test successful auxiliary openFDA adverse event lookup."""
    mock_resp = OpenFDAEventSearchResponse(
        drug="aspirin",
        event="bleeding",
        total=45,
        results=[
            OpenFDAEventItem(
                safetyreportid="10023481",
                receivedate="20240210",
                serious="1",
                seriousnessdeath="0",
                patient_age="68",
                patient_sex="1",
                drugs=["ASPIRIN"],
                reactions=["GASTROINTESTINAL BLEEDING"],
            )
        ],
    )

    with patch.object(OpenFDAClient, "search_events", return_value=mock_resp):
        response = client.get("/api/v1/openfda/events/search?drug=aspirin&event=bleeding")

    assert response.status_code == 200
    data = response.json()
    assert data["drug"] == "aspirin"
    assert data["event"] == "bleeding"
    assert data["total"] == 45
    assert data["source"] == "openFDA"
    assert data["is_auxiliary_lookup"] is True
    assert len(data["results"]) == 1
    assert data["results"][0]["safetyreportid"] == "10023481"
    assert "GASTROINTESTINAL BLEEDING" in data["results"][0]["reactions"]


def test_openfda_event_search_missing_params(client: TestClient):
    """Test rejection when neither drug nor event query parameter is provided."""
    response = client.get("/api/v1/openfda/events/search")
    assert response.status_code == 400
    error = response.json()
    assert "at least one of 'drug' or 'event'" in error["error"]["message"].lower()


def test_openfda_timeout_handling(client: TestClient):
    """Test handling openFDA request timeout."""
    with patch.object(OpenFDAClient, "search_drugs", side_effect=OpenFDATimeoutError("Timed out")):
        response = client.get("/api/v1/openfda/drugs/search?q=aspirin")

    assert response.status_code == 504
    error = response.json()
    assert "timed out" in error["error"]["message"].lower()


def test_openfda_upstream_server_error(client: TestClient):
    """Test handling openFDA 500 error."""
    with patch.object(OpenFDAClient, "search_drugs", side_effect=OpenFDAAPIError("Server error")):
        response = client.get("/api/v1/openfda/drugs/search?q=aspirin")

    assert response.status_code == 502
    error = response.json()
    assert "failed to retrieve data from openfda" in error["error"]["message"].lower()


def test_openfda_auth_error(client: TestClient):
    """Test handling openFDA authentication failure."""
    with patch.object(OpenFDAClient, "search_drugs", side_effect=OpenFDAAuthError("Auth error")):
        response = client.get("/api/v1/openfda/drugs/search?q=aspirin")

    assert response.status_code == 503
    error = response.json()
    assert "authentication failed" in error["error"]["message"].lower()


def test_openfda_client_unit_parsing():
    """Unit test OpenFDAClient methods and parsing logic directly."""
    client = OpenFDAClient(base_url="https://api.fda.gov", api_key="test-api-key")

    # Test params builder attaches key
    params = client._build_params({"search": "aspirin"})
    assert params["api_key"] == "test-api-key"
    assert params["search"] == "aspirin"

    # Test drug search with mocked _execute_get
    with patch.object(client, "_execute_get", return_value=sample_openfda_drug_payload()):
        resp = client.search_drugs("aspirin")
        assert resp.total == 1
        assert len(resp.results) == 1
        assert resp.results[0].brand_name == ["ASPIRIN 81MG"]

    # Test event search with mocked _execute_get
    with patch.object(client, "_execute_get", return_value=sample_openfda_event_payload()):
        ev_resp = client.search_events(drug="aspirin", event="bleeding")
        assert ev_resp.total == 45
        assert len(ev_resp.results) == 1
        assert ev_resp.results[0].safetyreportid == "10023481"


def test_openfda_api_key_not_leaked(client: TestClient):
    """Ensure that the openFDA API key is never returned in client response bodies."""
    app = client.app
    app.dependency_overrides[get_app_settings] = lambda: Settings(openfda_api_key="super_secret_fda_key_123")

    mock_resp = OpenFDADrugSearchResponse(query="aspirin", total=1, results=[])
    with patch.object(OpenFDAClient, "search_drugs", return_value=mock_resp):
        response = client.get("/api/v1/openfda/drugs/search?q=aspirin")

    assert response.status_code == 200
    assert "super_secret_fda_key_123" not in response.text


def test_core_signal_endpoints_remain_independent_of_openfda(client: TestClient):
    """
    Verify core SignalTrace endpoints (/api/v1/signals) continue to work normally
    even if openFDA is completely offline or configured with an invalid domain.
    """
    app = client.app
    # Break openFDA configuration intentionally
    app.dependency_overrides[get_app_settings] = lambda: Settings(
        openfda_api_base_url="https://nonexistent-openfda-offline-domain.invalid"
    )

    # Core signal listing should succeed from local database
    sig_list = client.get("/api/v1/signals")
    assert sig_list.status_code == 200
    sig_data = sig_list.json()
    assert "items" in sig_data
    assert sig_data["total"] >= 1

    # Core signal detail should succeed from local database
    sig_detail = client.get("/api/v1/signals/sig-001")
    assert sig_detail.status_code == 200
    detail_data = sig_detail.json()
    assert detail_data["signal_id"] == "sig-001"
    assert detail_data["drug_name"] == "ASPIRIN"
    # Verify deterministic PRR from pipeline is preserved
    assert detail_data["prr"] == 3.4
