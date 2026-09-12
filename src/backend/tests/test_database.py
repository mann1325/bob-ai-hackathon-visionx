from unittest.mock import patch
import pytest
from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient

from app.main import create_app
from database.session import get_db, get_engine


def test_db_dependency_when_unconfigured():
    app = create_app()

    @app.get("/test-db")
    def test_db_endpoint(db=Depends(get_db)):
        return {"ok": True}

    with patch("database.session._engine", None), patch("database.session._session_factory", None):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-db")
        assert response.status_code == 503
        body = response.json()
        assert "error" in body
        assert "Database connection is not configured" in body["error"]["message"]


def test_sqlite_engine_initialization(tmp_path):
    db_file = tmp_path / "test.db"
    sqlite_url = f"sqlite:///{db_file}"

    with patch("database.session.get_settings") as mock_settings:
        mock_settings.return_value.database_url = sqlite_url
        with patch("database.session._engine", None), patch("database.session._session_factory", None):
            engine = get_engine()
            assert engine is not None
            assert str(engine.url).startswith("sqlite")
