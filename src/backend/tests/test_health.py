def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "SignalTrace API"
    assert body["health"] == "/api/v1/health"


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "SignalTrace API"
    assert "environment" in body


def test_validation_error_format(client):
    response = client.get("/api/v1/health?invalid=not_used")
    assert response.status_code == 200
