from unittest.mock import patch

from database.models import SignalModel
from ai.groq_client import GroqClient


def review_payload(**overrides):
    payload = {
        "review_status": "in_review",
        "evidence_checklist": {
            "supporting_reports_reviewed": True,
            "case_quality_reviewed": True,
            "reporting_trend_reviewed": False,
            "duplicates_reviewed": False,
            "ai_explanation_reviewed": False,
            "regulatory_documents_reviewed": False,
        },
        "reviewer_notes": "Reviewed supporting evidence.",
        "reviewer_conclusion": "Human-authored conclusion pending final review.",
    }
    payload.update(overrides)
    return payload


def test_get_review_existing_signal_without_record(client):
    response = client.get("/api/v1/signals/sig-001/review")

    assert response.status_code == 200
    assert response.json() == {
        "review_id": None,
        "signal_id": "sig-001",
        "review_status": "not_started",
        "evidence_checklist": {
            "supporting_reports_reviewed": False,
            "case_quality_reviewed": False,
            "reporting_trend_reviewed": False,
            "duplicates_reviewed": False,
            "ai_explanation_reviewed": False,
            "regulatory_documents_reviewed": False,
        },
        "reviewer_notes": "",
        "reviewer_conclusion": "",
        "created_at": None,
        "updated_at": None,
    }


def test_put_creates_review_and_does_not_change_candidate_status(client, db_session):
    response = client.put("/api/v1/signals/sig-001/review", json=review_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["review_id"]
    assert body["signal_id"] == "sig-001"
    assert body["review_status"] == "in_review"
    assert body["reviewer_notes"] == "Reviewed supporting evidence."
    assert body["reviewer_conclusion"].startswith("Human-authored")
    assert db_session.get(SignalModel, "sig-001").candidate_status == "candidate"


def test_get_review_returns_saved_fields(client):
    client.put("/api/v1/signals/sig-001/review", json=review_payload())

    response = client.get("/api/v1/signals/sig-001/review")

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "in_review"
    assert body["evidence_checklist"]["case_quality_reviewed"] is True
    assert body["reviewer_notes"] == "Reviewed supporting evidence."
    assert body["reviewer_conclusion"].startswith("Human-authored")


def test_put_updates_existing_review_and_persists_checklist(client):
    created = client.put("/api/v1/signals/sig-001/review", json=review_payload()).json()
    updated = client.put(
        "/api/v1/signals/sig-001/review",
        json=review_payload(
            review_status="reviewed",
            evidence_checklist={
                "supporting_reports_reviewed": True,
                "case_quality_reviewed": True,
                "reporting_trend_reviewed": True,
                "duplicates_reviewed": True,
                "ai_explanation_reviewed": True,
                "regulatory_documents_reviewed": True,
            },
            reviewer_notes="All evidence reviewed.",
            reviewer_conclusion="Human-authored conclusion: retain for continued monitoring.",
        ),
    ).json()

    assert updated["review_id"] == created["review_id"]
    assert updated["review_status"] == "reviewed"
    assert all(updated["evidence_checklist"].values())
    assert updated["reviewer_notes"] == "All evidence reviewed."
    assert "Human-authored" in updated["reviewer_conclusion"]


def test_review_unknown_signal_returns_404(client):
    assert client.get("/api/v1/signals/no-such-signal/review").status_code == 404
    assert client.put("/api/v1/signals/no-such-signal/review", json=review_payload()).status_code == 404


def test_review_rejects_invalid_status(client):
    response = client.put(
        "/api/v1/signals/sig-001/review",
        json=review_payload(review_status="approved"),
    )
    assert response.status_code == 422


def test_ai_explanation_does_not_overwrite_reviewer_fields(client):
    client.put(
        "/api/v1/signals/sig-001/review",
        json=review_payload(reviewer_notes="Human note", reviewer_conclusion="Human conclusion"),
    )

    with patch("services.explanation_service.get_settings") as settings, \
         patch.object(
             GroqClient,
             "generate_explanation",
             return_value={
                 "why_flagged": "AI explanation",
                 "evidence_summary": "AI summary",
                 "limitations": [],
                 "suggested_questions": [],
             },
         ):
        settings.return_value.groq_api_key = "gsk_test_key"
        assert client.post("/api/v1/signals/sig-001/explain").status_code == 200

    saved = client.get("/api/v1/signals/sig-001/review").json()
    assert saved["reviewer_notes"] == "Human note"
    assert saved["reviewer_conclusion"] == "Human conclusion"
