from database.models import SignalModel


def test_investigation_summary_returns_existing_evidence(client):
    response = client.get("/api/v1/signals/sig-001/investigation-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["signal_id"] == "sig-001"
    assert body["drug_name"] == "ASPIRIN"
    assert body["event_name"] == "GASTROINTESTINAL BLEEDING"
    assert body["supporting_report_count"] == 120
    assert body["prr"] == 3.4
    assert body["ror"] == 2.8
    assert body["chi_square"] == 45.2
    assert body["trend_data"] == [
        {"quarter": "2023Q3", "count": 25},
        {"quarter": "2023Q4", "count": 40},
        {"quarter": "2024Q1", "count": 55},
    ]
    assert body["case_quality"]["total_reports"] == 120
    assert body["duplicate_count"] == 1
    assert body["human_review"] is not None
    assert body["documents"] == []


def test_investigation_summary_unknown_signal_returns_404(client):
    response = client.get("/api/v1/signals/no-such-signal/investigation-summary")
    assert response.status_code == 404


def test_investigation_summary_represents_unavailable_trend(client):
    response = client.get("/api/v1/signals/sig-002/investigation-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["trend_data"] == [{"quarter": "2024Q1", "count": 1}]
    assert body["trend_score"] == 0.6
    assert body["case_quality"] is not None


def test_investigation_summary_does_not_mutate_signal(client, db_session):
    before = db_session.get(SignalModel, "sig-001")
    before_status = before.candidate_status

    response = client.get("/api/v1/signals/sig-001/investigation-summary")

    assert response.status_code == 200
    db_session.expire_all()
    after = db_session.get(SignalModel, "sig-001")
    assert after.candidate_status == before_status == "candidate"
