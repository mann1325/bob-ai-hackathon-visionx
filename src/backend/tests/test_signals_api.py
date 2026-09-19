import pytest

from database.models import SignalMetricsModel, SignalModel


def test_list_signals_default(client):
    response = client.get("/api/v1/signals")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 3
    assert len(body["items"]) == 3
    # Check default rank sorting (asc)
    assert body["items"][0]["signal_id"] == "sig-001"
    assert body["items"][0]["rank"] == 1


def test_list_signals_filter_by_drug(client):
    response = client.get("/api/v1/signals?drug=WARFARIN")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["drug_name"] == "WARFARIN"


def test_list_signals_filter_by_event(client):
    response = client.get("/api/v1/signals?event=BLEEDING")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["signal_id"] == "sig-001"


def test_list_signals_filter_by_min_prr(client):
    response = client.get("/api/v1/signals?min_prr=3.0")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["prr"] >= 3.0


def test_list_signals_filter_by_status(client):
    response = client.get("/api/v1/signals?status=under_review")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["candidate_status"] == "under_review"


def test_list_signals_filter_by_release(client):
    response = client.get("/api/v1/signals?release_id=2023Q4")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["signal_id"] == "sig-003"


def test_list_signals_sorting(client):
    response = client.get("/api/v1/signals?sort_by=prr&sort_order=desc")
    assert response.status_code == 200
    body = response.json()
    prrs = [item["prr"] for item in body["items"]]
    assert prrs == sorted(prrs, reverse=True)


def test_list_signals_pagination(client):
    response = client.get("/api/v1/signals?page=1&page_size=2")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["pages"] == 2
    assert body["page"] == 1


def test_list_signals_computes_trend_score_from_metrics(db_session, client):
    db_session.add(
        SignalModel(
            signal_id="SIG-9A30F2C9A6",
            drug_name="DUPIXENT",
            event_name="DERMATITIS ATOPIC",
            supporting_report_count=4279,
            prr=168.76,
            ror=176.71,
            trend_score=None,
            risk_score=1.0,
            priority_level="critical",
            candidate_status="candidate",
            dataset_version="2026Q1",
            rank=4,
        )
    )
    db_session.add(
        SignalMetricsModel(
            signal_id="SIG-9A30F2C9A6",
            prr=168.76,
            ror=176.71,
            report_count=4279,
            trend_data=[
                {"quarter": "2025Q4", "count": 4907},
                {"quarter": "2026Q1", "count": 4279},
            ],
        )
    )
    db_session.flush()

    response = client.get("/api/v1/signals?drug=DUPIXENT&event=DERMATITIS%20ATOPIC")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["signal_id"] == "SIG-9A30F2C9A6"
    assert item["trend_score"] == pytest.approx(-0.13673, abs=1e-6)


def test_get_signal_detail_success(client):
    response = client.get("/api/v1/signals/sig-001")
    assert response.status_code == 200
    body = response.json()
    assert body["signal_id"] == "sig-001"
    assert body["drug_name"] == "ASPIRIN"
    assert body["event_name"] == "GASTROINTESTINAL BLEEDING"
    assert body["prr"] == 3.4
    assert body["ror"] == 2.8
    assert body["trend_score"] == 0.375
    assert body["human_review_required"] is True
    assert "metrics" in body
    assert body["metrics"]["chi_square"] == 45.2
    assert len(body["known_limitations"]) >= 1


def test_get_signal_detail_returns_null_trend_score_for_one_quarter(client):
    response = client.get("/api/v1/signals/sig-002")

    assert response.status_code == 200
    assert response.json()["trend_score"] is None


def test_get_signal_detail_not_found(client):
    response = client.get("/api/v1/signals/sig-unknown")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert "not found" in body["error"]["message"].lower()


def test_get_signal_metrics_success(client):
    response = client.get("/api/v1/signals/sig-001/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["signal_id"] == "sig-001"
    assert body["prr"] == 3.4
    assert body["contingency_table"]["a"] == 120
    assert len(body["trend_data"]) == 3


def test_get_signal_metrics_not_found(client):
    response = client.get("/api/v1/signals/sig-unknown/metrics")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"


def test_get_signal_evidence_success(client):
    response = client.get("/api/v1/signals/sig-001/evidence")
    assert response.status_code == 200
    body = response.json()
    assert body["signal_id"] == "sig-001"
    assert body["drug_name"] == "ASPIRIN"
    assert body["human_review_required"] is True
    # Case quality checks
    assert body["case_quality"] is not None
    assert body["case_quality"]["quality_score"] == 0.88
    # Duplicate candidates checks
    assert len(body["potential_duplicates"]) == 1
    assert body["potential_duplicates"][0]["candidate_id"] == "dup-001"
    assert body["potential_duplicates"][0]["status"] == "potential_duplicate"


def test_get_signal_evidence_not_found(client):
    response = client.get("/api/v1/signals/sig-unknown/evidence")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"


def test_get_signal_reports_scopes_by_drug_event_and_quarter(client):
    response = client.get("/api/v1/signals/sig-001/reports")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [report["report_id"] for report in body["reports"]] == ["rep-001", "rep-002"]
    assert body["reports"][0]["reactions"] == ["GASTROINTESTINAL BLEEDING", "NAUSEA"]


def test_get_signal_reports_pagination(client):
    response = client.get("/api/v1/signals/sig-001/reports?page=2&page_size=1")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 1
    assert body["total"] == 2
    assert [report["report_id"] for report in body["reports"]] == ["rep-002"]


def test_get_signal_reports_empty_results(client):
    response = client.get("/api/v1/signals/sig-003/reports")
    assert response.status_code == 200
    assert response.json() == {"reports": [], "total": 0, "page": 1, "page_size": 50}


def test_get_signal_reports_nonexistent_signal(client):
    response = client.get("/api/v1/signals/sig-unknown/reports")
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_get_report_by_id_success_and_schema(client):
    response = client.get("/api/v1/reports/rep-001")
    assert response.status_code == 200
    assert response.json() == {
        "report_id": "rep-001",
        "drug_name": "ASPIRIN",
        "reactions": ["GASTROINTESTINAL BLEEDING", "NAUSEA"],
        "patient_age": 62.0,
        "patient_sex": "M",
        "event_date": "2024-01-15",
        "seriousness": "Serious",
        "seriousness_codes": ["DE", "HO"],
        "report_quarter": "2024Q1",
        "source": "FDA_FAERS",
    }


def test_get_report_by_id_preserves_missing_values(client):
    response = client.get("/api/v1/reports/rep-002")
    assert response.status_code == 200
    body = response.json()
    assert body["patient_age"] is None
    assert body["patient_sex"] is None
    assert body["event_date"] is None
    assert body["seriousness"] == "Unknown"
    assert body["seriousness_codes"] == []


def test_get_report_by_id_not_found(client):
    response = client.get("/api/v1/reports/rep-unknown")
    assert response.status_code == 404
    assert response.json()["status"] == "error"
