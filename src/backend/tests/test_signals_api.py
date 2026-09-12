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


def test_get_signal_detail_success(client):
    response = client.get("/api/v1/signals/sig-001")
    assert response.status_code == 200
    body = response.json()
    assert body["signal_id"] == "sig-001"
    assert body["drug_name"] == "ASPIRIN"
    assert body["event_name"] == "GASTROINTESTINAL BLEEDING"
    assert body["prr"] == 3.4
    assert body["ror"] == 2.8
    assert body["human_review_required"] is True
    assert "metrics" in body
    assert body["metrics"]["chi_square"] == 45.2
    assert len(body["known_limitations"]) >= 1


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
