from database.models import DuplicateCandidateModel, ProcessedReportModel
from services.investigation_service import get_duplicate_candidates_for_signal


def test_get_case_quality_prematerialized(client):
    response = client.get("/api/v1/signals/sig-001/case-quality")
    assert response.status_code == 200
    body = response.json()
    assert body["signal_id"] == "sig-001"
    assert body["total_reports"] == 120
    assert body["missing_age_count"] == 12
    assert body["missing_sex_count"] == 5
    assert body["missing_date_count"] == 8
    assert body["quality_score"] == 0.88
    assert len(body["indicators"]) >= 1
    assert body["indicators"][0]["flag"] == "missing_age"


def test_get_case_quality_compute_on_read(client):
    # sig-002 has no pre-materialized case_quality row
    response = client.get("/api/v1/signals/sig-002/case-quality")
    assert response.status_code == 200
    body = response.json()
    assert body["signal_id"] == "sig-002"
    assert "quality_score" in body
    assert body["quality_score"] >= 0.0


def test_get_case_quality_not_found(client):
    response = client.get("/api/v1/signals/sig-nonexistent/case-quality")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert "not found" in body["error"]["message"].lower()


def test_get_duplicates_prematerialized(client):
    response = client.get("/api/v1/signals/sig-001/duplicates")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    dup = body[0]
    assert dup["candidate_id"] == "dup-001"
    assert dup["report_id_a"] == "r-101"
    assert dup["report_id_b"] == "r-102"
    assert dup["status"] == "potential_duplicate"
    assert dup["similarity_score"] == 0.92
    assert dup["drug_similarity"] == 1.0
    assert dup["event_similarity"] == 1.0
    assert dup["date_proximity_days"] == 3
    assert "drug" in dup["matched_fields"]
    assert "event" in dup["matched_fields"]
    assert dup["human_review_required"] is True
    assert "human triage" in dup["disclaimer"].lower()


def test_get_duplicates_empty_when_none(client):
    # sig-002 has no duplicate candidates
    response = client.get("/api/v1/signals/sig-002/duplicates")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body == []


def test_get_duplicates_not_found(client):
    response = client.get("/api/v1/signals/sig-nonexistent/duplicates")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert "not found" in body["error"]["message"].lower()


def test_duplicate_never_auto_confirmed_or_deleted(client):
    response = client.get("/api/v1/signals/sig-001/duplicates")
    assert response.status_code == 200
    for dup in response.json():
        assert dup["status"] == "potential_duplicate"
        assert dup["human_review_required"] is True
        assert "prohibited" in dup["disclaimer"].lower()


def test_duplicate_candidates_generate_from_blocked_reports(db_session):
    db_session.add_all(
        [
            ProcessedReportModel(
                report_id="real-a",
                drug_name="WARFARIN",
                reactions=["HAEMORRHAGE"],
                patient_age=62,
                patient_sex="M",
                event_date="2026-01-15",
                report_quarter="2024Q1",
                source="FDA_FAERS",
            ),
            ProcessedReportModel(
                report_id="real-b",
                drug_name="WARFARIN",
                reactions=["HAEMORRHAGE"],
                patient_age=62,
                patient_sex="M",
                event_date="2026-01-15",
                report_quarter="2024Q1",
                source="FDA_FAERS",
            ),
            ProcessedReportModel(
                report_id="different-event",
                drug_name="WARFARIN",
                reactions=["NAUSEA"],
                patient_age=62,
                patient_sex="M",
                event_date="2026-01-15",
                report_quarter="2024Q1",
                source="FDA_FAERS",
            ),
        ]
    )
    db_session.flush()

    candidates = get_duplicate_candidates_for_signal(db_session, "sig-002")

    assert candidates is not None
    assert len(candidates) == 1
    candidate = candidates[0]
    assert {candidate.report_id_a, candidate.report_id_b} == {"real-a", "real-b"}
    assert candidate.status == "potential_duplicate"
    assert candidate.similarity_score == 1.0
    assert candidate.date_proximity_days == 0
    assert candidate.matched_fields == ["drug", "event", "age", "sex", "event_date"]
    assert candidate.human_review_required is True
    assert "not confirmation" in candidate.rationale


def test_duplicate_generation_is_idempotent_and_excludes_self_pairs(db_session):
    db_session.add_all(
        [
            ProcessedReportModel(
                report_id="stable-a",
                drug_name="WARFARIN",
                reactions=["HAEMORRHAGE"],
                patient_age=60,
                patient_sex="F",
                event_date="2026-02-01",
                report_quarter="2024Q1",
                source="FDA_FAERS",
            ),
            ProcessedReportModel(
                report_id="stable-b",
                drug_name="WARFARIN",
                reactions=["HAEMORRHAGE"],
                patient_age=60,
                patient_sex="F",
                event_date="2026-02-01",
                report_quarter="2024Q1",
                source="FDA_FAERS",
            ),
        ]
    )
    db_session.flush()

    first = get_duplicate_candidates_for_signal(db_session, "sig-002")
    first_ids = {candidate.candidate_id for candidate in first or []}
    first_row_count = db_session.query(DuplicateCandidateModel).count()
    second = get_duplicate_candidates_for_signal(db_session, "sig-002")
    second_ids = {candidate.candidate_id for candidate in second or []}

    assert first_ids == second_ids
    assert first_row_count == db_session.query(DuplicateCandidateModel).count()
    assert all(candidate.report_id_a != candidate.report_id_b for candidate in second or [])
