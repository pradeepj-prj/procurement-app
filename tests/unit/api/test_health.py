from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Set GRAPH_BACKEND before importing the app so the lifespan uses NetworkX
os.environ.setdefault("GRAPH_BACKEND", "networkx")

from app.api.router import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    """TestClient with lifespan — triggers startup so app.state.backend exists."""
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_healthy(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"

    def test_includes_version(self, client):
        data = client.get("/health").json()
        assert data["version"] == "2.0.0"

    def test_includes_timestamp(self, client):
        data = client.get("/health").json()
        assert "timestamp" in data


class TestReadyEndpoint:
    def test_returns_200_with_networkx(self, client):
        response = client.get("/ready")
        assert response.status_code == 200

    def test_status_ready(self, client):
        data = client.get("/ready").json()
        assert data["status"] == "ready"

    def test_database_check_ok(self, client):
        data = client.get("/ready").json()
        assert data["checks"]["database"] == "ok"


class TestCORS:
    def test_cors_preflight(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_disallowed_origin(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in response.headers
