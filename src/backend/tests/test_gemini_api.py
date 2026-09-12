import json
from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from ai.gemini_client import (
    DEFAULT_GEMINI_MODEL,
    GeminiAPIError,
    GeminiAuthError,
    GeminiClient,
)
from app.config import Settings
from app.dependencies import get_app_settings
from database.models import DocumentAnalysisModel, DocumentUploadModel


@pytest.fixture
def sample_document(db_session):
    """Seed a sample document with extracted text linked to sig-001."""
    doc = DocumentUploadModel(
        document_id="doc-test-001",
        filename="aspirin_core_data_sheet.txt",
        file_type="txt",
        file_size_bytes=512,
        signal_id="sig-001",
        extracted_text=(
            "Aspirin Core Data Sheet.\n"
            "Section 4.4 Warnings and Precautions: Risk of gastric mucosal damage.\n"
            "Section 4.8 Undesirable effects: Dyspepsia, nausea, abdominal pain."
        ),
        extracted_text_preview="Aspirin Core Data Sheet. Section 4.4 Warnings and Precautions...",
        status="extracted",
    )
    db_session.add(doc)
    db_session.commit()
    return doc


def test_gemini_prompt_building():
    """Verify prompt formatting contains document text and candidate signal context."""
    client = GeminiClient(api_key="test-key")
    signal_ctx = {
        "signal_id": "sig-001",
        "drug_name": "ASPIRIN",
        "event_name": "GASTROINTESTINAL BLEEDING",
        "report_count": 120,
        "prr": 3.4,
        "review_areas": ["Product Label", "PSUR / PBRER"],
    }
    doc_text = "Section 4.4: Gastrointestinal ulceration precautions."
    prompt = client._build_user_prompt(doc_text, "label.txt", signal_ctx)

    assert "ASPIRIN" in prompt
    assert "GASTROINTESTINAL BLEEDING" in prompt
    assert "PRR: 3.4" in prompt
    assert "Product Label" in prompt
    assert "Gastrointestinal ulceration" in prompt


def test_gemini_json_parsing_with_code_fences():
    """Verify JSON parsing handles markdown fences and normalizes fields."""
    client = GeminiClient(api_key="test-key")
    raw_text = """```json
    {
        "relevant_sections": [
            {"section_name": "Section 4.4", "relevance_reason": "Contains warnings on ulceration."}
        ],
        "existing_related_content": "Ulceration mentioned in Section 4.4.",
        "potential_coverage_gap": "Potential coverage gap regarding severe haemorrhage risk.",
        "analysis_status": "completed"
    }
    ```"""
    parsed = client._parse_json_response(raw_text)
    assert len(parsed["relevant_sections"]) == 1
    assert parsed["relevant_sections"][0]["section_name"] == "Section 4.4"
    assert "Ulceration mentioned" in parsed["existing_related_content"]
    assert "Potential coverage gap" in parsed["potential_coverage_gap"]
    assert parsed["analysis_status"] == "completed"


def test_analyze_document_success(client: TestClient, sample_document, db_session):
    """Test successful document analysis with mocked GeminiClient."""
    app = client.app
    test_settings = Settings(gemini_api_key="valid-test-gemini-key")
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    mock_analysis = {
        "relevant_sections": [
            {
                "section_name": "Section 4.4 Special Warnings",
                "relevance_reason": "Discusses gastric mucosal irritation and bleeding precautions.",
            },
            {
                "section_name": "Section 4.8 Undesirable Effects",
                "relevance_reason": "Lists gastrointestinal adverse reactions.",
            },
        ],
        "existing_related_content": "Section 4.4 mentions gastric mucosal damage.",
        "potential_coverage_gap": "Potential coverage gap: Severe upper gastrointestinal bleeding risk may warrant updated warnings.",
        "analysis_status": "completed",
    }

    with patch.object(GeminiClient, "analyze_document", return_value=mock_analysis):
        response = client.post("/api/v1/documents/doc-test-001/analyze")

    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == "doc-test-001"
    assert data["signal_id"] == "sig-001"
    assert len(data["relevant_sections"]) == 2
    assert "Section 4.4" in data["relevant_sections"][0]["section_name"]
    assert "gastric mucosal damage" in data["existing_related_content"]
    assert "Potential coverage gap" in data["potential_coverage_gap"]
    assert data["human_review_required"] is True
    assert "disclaimer" in data
    assert "human review" in data["disclaimer"].lower()

    # Verify database persistence
    saved_analysis = (
        db_session.query(DocumentAnalysisModel)
        .filter_by(document_id="doc-test-001")
        .first()
    )
    assert saved_analysis is not None
    assert saved_analysis.signal_id == "sig-001"
    assert saved_analysis.human_review_required is True


def test_get_document_analysis_success(client: TestClient, sample_document, db_session):
    """Test retrieving stored document analysis via GET endpoint."""
    app = client.app
    test_settings = Settings(gemini_api_key="valid-test-gemini-key")
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    mock_analysis = {
        "relevant_sections": [
            {
                "section_name": "Section 4.4",
                "relevance_reason": "Bleeding warnings",
            }
        ],
        "existing_related_content": "Warnings present.",
        "potential_coverage_gap": "Potential coverage gap identified.",
        "analysis_status": "completed",
    }

    with patch.object(GeminiClient, "analyze_document", return_value=mock_analysis):
        client.post("/api/v1/documents/doc-test-001/analyze")

    get_resp = client.get("/api/v1/documents/doc-test-001/analysis")
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["document_id"] == "doc-test-001"
    assert len(data["relevant_sections"]) == 1
    assert data["human_review_required"] is True


def test_get_document_analysis_not_found(client: TestClient, sample_document):
    """Test retrieving analysis when none has been performed yet."""
    response = client.get("/api/v1/documents/doc-test-001/analysis")
    assert response.status_code == 404
    error = response.json()
    assert "no analysis found" in error["error"]["message"].lower()


def test_analyze_document_not_found(client: TestClient):
    """Test analyzing a nonexistent document."""
    app = client.app
    app.dependency_overrides[get_app_settings] = lambda: Settings(gemini_api_key="valid-key")

    response = client.post("/api/v1/documents/doc-nonexistent-999/analyze")
    assert response.status_code == 404
    error = response.json()
    assert "not found" in error["error"]["message"].lower()


def test_analyze_document_no_extracted_text(client: TestClient, db_session):
    """Test analyzing a document with empty extracted text."""
    app = client.app
    app.dependency_overrides[get_app_settings] = lambda: Settings(gemini_api_key="valid-key")

    doc = DocumentUploadModel(
        document_id="doc-empty-text",
        filename="empty.txt",
        file_type="txt",
        file_size_bytes=0,
        extracted_text="",
        status="uploaded",
    )
    db_session.add(doc)
    db_session.commit()

    response = client.post("/api/v1/documents/doc-empty-text/analyze")
    assert response.status_code == 400
    error = response.json()
    assert "extracted text" in error["error"]["message"].lower()


def test_analyze_document_missing_gemini_api_key(client: TestClient, sample_document):
    """Test graceful 503 response when GEMINI_API_KEY is not configured."""
    app = client.app
    app.dependency_overrides[get_app_settings] = lambda: Settings(gemini_api_key=None)

    response = client.post("/api/v1/documents/doc-test-001/analyze")
    assert response.status_code == 503
    error = response.json()
    assert "gemini_api_key is not configured" in error["error"]["message"].lower()


def test_analyze_document_gemini_auth_failure(client: TestClient, sample_document):
    """Test handling Gemini authentication failure."""
    app = client.app
    app.dependency_overrides[get_app_settings] = lambda: Settings(gemini_api_key="invalid-key")

    with patch.object(GeminiClient, "analyze_document", side_effect=GeminiAuthError("Authentication failed")):
        response = client.post("/api/v1/documents/doc-test-001/analyze")

    assert response.status_code == 503
    error = response.json()
    assert "authentication failed" in error["error"]["message"].lower()


def test_analyze_document_gemini_timeout(client: TestClient, sample_document):
    """Test handling Gemini timeout / network error."""
    app = client.app
    app.dependency_overrides[get_app_settings] = lambda: Settings(gemini_api_key="valid-key")

    with patch.object(GeminiClient, "analyze_document", side_effect=GeminiAPIError("Timeout connecting to Gemini")):
        response = client.post("/api/v1/documents/doc-test-001/analyze")

    assert response.status_code == 502
    error = response.json()
    assert "failed to retrieve ai document analysis" in error["error"]["message"].lower()


def test_analyze_document_malformed_json_fallback(client: TestClient, sample_document):
    """Test handling non-JSON plain text response with safe fallback."""
    app = client.app
    app.dependency_overrides[get_app_settings] = lambda: Settings(gemini_api_key="valid-key")

    fallback_analysis = {
        "relevant_sections": [
            {
                "section_name": "General Safety",
                "relevance_reason": "Automated fallback parsing.",
            }
        ],
        "existing_related_content": "Unstructured content",
        "potential_coverage_gap": "Potential coverage gap requires human expert verification.",
        "analysis_status": "needs_review",
    }

    with patch.object(GeminiClient, "analyze_document", return_value=fallback_analysis):
        response = client.post("/api/v1/documents/doc-test-001/analyze")

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_status"] == "needs_review"
    assert data["human_review_required"] is True
    assert len(data["relevant_sections"]) > 0


def test_get_signal_documents_endpoint(client: TestClient, sample_document, db_session):
    """Test GET /api/v1/signals/{signal_id}/documents."""
    app = client.app
    test_settings = Settings(gemini_api_key="valid-test-gemini-key")
    app.dependency_overrides[get_app_settings] = lambda: test_settings

    mock_analysis = {
        "relevant_sections": [{"section_name": "Section 4", "relevance_reason": "Risk overview"}],
        "existing_related_content": "Summary content.",
        "potential_coverage_gap": "Potential gap.",
        "analysis_status": "completed",
    }

    with patch.object(GeminiClient, "analyze_document", return_value=mock_analysis):
        client.post("/api/v1/documents/doc-test-001/analyze")

    resp = client.get("/api/v1/signals/sig-001/documents")
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["document"]["document_id"] == "doc-test-001"
    assert data[0]["analysis"] is not None
    assert data[0]["analysis"]["document_id"] == "doc-test-001"


def test_get_signal_documents_not_found(client: TestClient):
    """Test GET /api/v1/signals/{signal_id}/documents with invalid signal_id."""
    resp = client.get("/api/v1/signals/sig-nonexistent/documents")
    assert resp.status_code == 404
    error = resp.json()
    assert "not found" in error["error"]["message"].lower()
