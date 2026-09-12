from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import create_app


class ItemPayload(BaseModel):
    name: str
    count: int


def test_404_handler():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "http_404"


def test_422_validation_handler():
    app = create_app()

    @app.post("/test-validation")
    def create_item(payload: ItemPayload):
        return payload

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/test-validation", json={"name": "test", "count": "invalid_int"})
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "validation_error"


def test_500_unhandled_exception_handler():
    app = create_app()
    app.debug = False

    @app.get("/test-error")
    def trigger_error():
        raise RuntimeError("Something went wrong internally")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-error")
    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "internal_error"
