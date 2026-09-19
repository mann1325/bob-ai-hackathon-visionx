import json
from unittest.mock import MagicMock, patch
import pytest

from ai.groq_client import DEFAULT_GROQ_MODEL, GroqAPIError, GroqAuthError, GroqClient
from app.config import get_settings
from database.models import AISummaryModel
from services.explanation_service import build_explanation_facts
from services.signal_service import get_signal_evidence


def test_explanation_facts_include_existing_deterministic_evidence(db_session):
    evidence = get_signal_evidence(db_session, "sig-001")
    facts = build_explanation_facts(evidence)

    assert facts["report_count"] == 120
    assert facts["prr"] == 3.4
    assert facts["ror"] == 2.8
    assert facts["chi_square"] == 45.2
    assert facts["contingency_table"]["a"] == 120
    assert facts["case_quality"]["quality_score"] == 0.88
    assert facts["case_quality"]["missing_age_count"] == 12
    assert facts["case_quality"]["missing_sex_count"] == 5
    assert facts["case_quality"]["missing_date_count"] == 8
    assert facts["case_quality"]["quality_flags"] == ["minor_missing_dates"]
    assert facts["duplicate_count"] == 1
    assert facts["known_limitations"]
    assert "regulatory_review_areas" in facts
    assert "regulatory_rule_matches" in facts


def test_prompt_uses_structured_facts_only():
    client = GroqClient(api_key="gsk_test123")
    facts = {
        "drug_name": "ASPIRIN",
        "event_name": "GASTROINTESTINAL BLEEDING",
        "report_count": 120,
        "prr": 3.4,
        "ror": 2.8,
        "trend_score": 0.85,
        "chi_square": 45.2,
        "contingency_table": {"a": 120, "b": 500, "c": 300, "d": 20000},
        "trend_data": [{"quarter": "2024Q1", "count": 55}],
        "case_quality": {
            "quality_score": 0.88,
            "total_reports": 120,
            "missing_age_count": 12,
            "missing_sex_count": 5,
            "missing_date_count": 8,
            "quality_flags": ["minor_missing_dates"],
            "indicators": [{"flag": "missing_age", "impact_level": "low"}],
        },
        "duplicate_count": 1,
        "duplicate_sample": [{"rationale": "Identical drug, event, age 62M"}],
        "known_limitations": ["Spontaneous reporting bias"],
        "regulatory_review_areas": [{"document_type": "Product Label"}],
        "regulatory_rule_matches": [{"rule_id": "REG-001", "condition_matched": "PRR threshold"}],
    }
    prompt = client._build_user_prompt(facts)
    assert "ASPIRIN" in prompt
    assert "GASTROINTESTINAL BLEEDING" in prompt
    assert "PRR (Proportional Reporting Ratio): 3.4" in prompt
    assert "ROR (Reporting Odds Ratio): 2.8" in prompt
    assert "Trend Score: 0.85" in prompt
    assert "Case Quality Score: 0.88" in prompt
    assert "Missing Age Count: 12" in prompt
    assert "Missing Sex Count: 5" in prompt
    assert "Missing Event Date Count: 8" in prompt
    assert "Chi-square (Pearson, existing calculation): 45.2" in prompt
    assert "Deterministic Rule Matches" in prompt
    assert "Potential Duplicate Candidates Count: 1" in prompt


def test_prompt_marks_missing_fields_without_erasing_present_quality_data():
    client = GroqClient(api_key="gsk_test123")
    prompt = client._build_user_prompt({
        "case_quality": {
            "quality_score": 0.79,
            "total_reports": 4279,
            "missing_age_count": 958,
            "missing_sex_count": 9,
            "missing_date_count": 1531,
            "quality_flags": ["minor_missing_age", "high_missing_date"],
            "indicators": [],
        },
        "trend_data": None,
    })
    assert "Case Quality Score: 0.79" in prompt
    assert "Missing Age Count: 958" in prompt
    assert "Missing Sex Count: 9" in prompt
    assert "Missing Event Date Count: 1531" in prompt
    assert "minor_missing_age, high_missing_date" in prompt
    assert "Trend Data: NOT AVAILABLE IN EVIDENCE BUNDLE" in prompt


def test_duplicate_prompt_context_is_bounded_and_explicitly_sampled():
    client = GroqClient(api_key="gsk_test123")
    facts = {
        "drug_name": "DUPIXENT",
        "event_name": "DERMATITIS ATOPIC",
        "duplicate_count": 3574,
        "duplicate_rationale_sample": [
            f"candidate rationale {index}" for index in range(3)
        ],
    }

    prompt = client._build_user_prompt(facts)

    assert "Potential Duplicate Candidates Count: 3574" in prompt
    assert "sample only; not exhaustive" in prompt
    assert "candidate rationale 2" in prompt
    assert "candidate rationale 3" not in prompt
    assert len(prompt) < 5000


def test_default_groq_model_is_available_model():
    assert DEFAULT_GROQ_MODEL == "openai/gpt-oss-120b"
    assert DEFAULT_GROQ_MODEL != "llama-3.3-70b-versatile"


def test_groq_client_json_parsing_with_code_fences():
    client = GroqClient(api_key="gsk_test123")
    raw_response = (
        "```json\n"
        "{\n"
        '  "why_flagged": "Disproportional reporting observed.",\n'
        '  "evidence_summary": "120 reports indicate high PRR.",\n'
        '  "limitations": ["Spontaneous bias"],\n'
        '  "suggested_questions": ["Check dosage distributions"]\n'
        "}\n"
        "```"
    )
    parsed = client._parse_json_response(raw_response, {"known_limitations": []})
    assert parsed["why_flagged"] == "Disproportional reporting observed."
    assert "120 reports indicate high PRR." in parsed["evidence_summary"]
    assert len(parsed["suggested_questions"]) == 1


def test_explain_success_with_mocked_groq(client, db_session):
    mock_explanation_dict = {
        "why_flagged": "High reporting disproportionality (PRR=3.4, ROR=2.8).",
        "evidence_summary": "120 spontaneous cases with rising quarterly trend.",
        "limitations": ["Spontaneous reporting bias", "Possible notoriety bias"],
        "suggested_questions": [
            "What is the concomitant medication history?",
            "Are cases clustered within specific age groups?",
        ],
    }

    with patch("services.explanation_service.get_settings") as mock_settings, \
         patch.object(GroqClient, "generate_explanation", return_value=mock_explanation_dict):
        mock_settings.return_value.groq_api_key = "gsk_valid_test_key"

        response = client.post("/api/v1/signals/sig-001/explain")
        assert response.status_code == 200
        body = response.json()
        assert body["signal_id"] == "sig-001"
        assert body["why_flagged"] == mock_explanation_dict["why_flagged"]
        assert mock_explanation_dict["evidence_summary"] in body["evidence_summary"]
        assert len(body["limitations"]) == 2
        assert len(body["suggested_questions"]) == 2
        assert body["human_review_required"] is True
        assert "human review" in body["disclaimer"].lower()
        assert db_session.query(AISummaryModel).filter_by(signal_id="sig-001").count() == 1


def test_model_output_cannot_hide_present_case_quality_facts():
    client = GroqClient(api_key="gsk_test123")
    facts = {
        "report_count": 4279,
        "prr": 168.76,
        "ror": 176.71,
        "chi_square": 50695.33,
        "case_quality": {
            "quality_score": 0.79,
            "total_reports": 4279,
            "missing_age_count": 958,
            "missing_sex_count": 9,
            "missing_date_count": 1531,
            "quality_flags": ["minor_missing_age", "high_missing_date"],
        },
        "duplicate_count": 3538,
        "trend_data": None,
        "regulatory_review_areas": [{"document_type": "Product Label"}],
        "regulatory_rule_matches": [{"rule_id": "REG-001"}],
    }
    parsed = client._parse_json_response(
        json.dumps({
            "evidence_summary": "Case-quality metrics were unavailable.",
            "limitations": ["Case-quality scores and missing-field counts are not available."],
            "why_flagged": "Candidate signal.",
            "suggested_questions": [],
        }),
        facts,
    )
    assert "score=0.79" in parsed["evidence_summary"]
    assert "missing_age=958" in parsed["evidence_summary"]
    assert "missing_event_date=1531" in parsed["evidence_summary"]
    assert all("not available" not in item.lower() for item in parsed["limitations"])


def test_explain_missing_api_key(client):
    with patch("services.explanation_service.get_settings") as mock_settings:
        mock_settings.return_value.groq_api_key = None

        response = client.post("/api/v1/signals/sig-001/explain")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "error"
        assert "GROQ_API_KEY is not configured" in body["error"]["message"]


def test_explain_signal_not_found(client):
    with patch("services.explanation_service.get_settings") as mock_settings:
        mock_settings.return_value.groq_api_key = "gsk_valid_test_key"

        response = client.post("/api/v1/signals/sig-nonexistent/explain")
        assert response.status_code == 404
        body = response.json()
        assert body["status"] == "error"
        assert "not found" in body["error"]["message"].lower()


def test_explain_groq_auth_failure(client):
    with patch("services.explanation_service.get_settings") as mock_settings, \
         patch.object(GroqClient, "generate_explanation", side_effect=GroqAuthError("Unauthorized")):
        mock_settings.return_value.groq_api_key = "gsk_invalid_key"

        response = client.post("/api/v1/signals/sig-001/explain")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "error"
        assert "authentication failed" in body["error"]["message"].lower()
        # Verify no secret key is exposed in error response
        assert "gsk_invalid_key" not in json.dumps(body)


def test_explain_groq_api_failure(client):
    with patch("services.explanation_service.get_settings") as mock_settings, \
         patch.object(GroqClient, "generate_explanation", side_effect=GroqAPIError("Service timeout")):
        mock_settings.return_value.groq_api_key = "gsk_valid_key"

        response = client.post("/api/v1/signals/sig-001/explain")
        assert response.status_code == 502
        body = response.json()
        assert body["status"] == "error"
        assert "Failed to retrieve AI explanation" in body["error"]["message"]


def test_explain_endpoint_contract_alias(client):
    mock_explanation_dict = {
        "why_flagged": "Candidate signal flagged by statistical threshold.",
        "evidence_summary": "120 reports.",
        "limitations": [],
        "suggested_questions": [],
    }
    with patch("services.explanation_service.get_settings") as mock_settings, \
         patch.object(GroqClient, "generate_explanation", return_value=mock_explanation_dict):
        mock_settings.return_value.groq_api_key = "gsk_valid_test_key"

        response = client.post("/api/v1/signals/sig-001/explanation")
        assert response.status_code == 200
        body = response.json()
        assert body["signal_id"] == "sig-001"
        assert body["human_review_required"] is True
