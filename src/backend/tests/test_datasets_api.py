def test_list_datasets(client):
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 2
    assert body[0]["release_id"] == "2024Q1"
    assert body[0]["quarter"] == "2024Q1"
    assert body[0]["dataset_release"] == "FAERS 2024 Q1"
    assert body[0]["total_reports"] == 1500000


def test_get_dataset_by_id_success(client):
    response = client.get("/api/v1/datasets/2024Q1")
    assert response.status_code == 200
    body = response.json()
    assert body["release_id"] == "2024Q1"
    assert body["processing_version"] == "v1.0.0"


def test_get_dataset_by_id_not_found(client):
    response = client.get("/api/v1/datasets/nonexistent_release")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert "not found" in body["error"]["message"].lower()
