def test_drug_search_success(client):
    response = client.get("/api/v1/drugs/search?q=ASP")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert any(d["drug_name"] == "ASPIRIN" for d in body)


def test_drug_search_fallback_to_reports(client):
    response = client.get("/api/v1/drugs/search?q=LISIN")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert any(d["drug_name"] == "LISINOPRIL" for d in body)


def test_drug_search_empty_result(client):
    response = client.get("/api/v1/drugs/search?q=NONEXISTENT_XYZ")
    assert response.status_code == 200
    body = response.json()
    assert body == []


def test_drug_search_missing_param_returns_422(client):
    response = client.get("/api/v1/drugs/search")
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "validation_error"
