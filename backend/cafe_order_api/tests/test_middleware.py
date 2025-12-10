"""Tests for middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cafe_order_api.middelware import ServiceHealthMiddleware


@pytest.fixture
def app_with_middleware():
    """Create a test app with the middleware."""
    app = FastAPI()
    app.add_middleware(ServiceHealthMiddleware)

    @app.get("/livez")
    async def health():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz():
        return {"status": "ok"}

    @app.get("/")
    async def root():
        return {"message": "root"}

    @app.get("/docs")
    async def docs():
        return {"docs": True}

    @app.get("/api/test")
    async def test_endpoint():
        return {"data": "test"}

    # Initialize state
    app.state.db_ready = True
    app.state.db_error = None
    app.state.redis_ready = True
    app.state.redis_error = None

    return app


class TestServiceHealthMiddleware:
    """Tests for ServiceHealthMiddleware."""

    def test_livez_endpoint_always_accessible(self, app_with_middleware):
        """Test that /livez endpoint works even when services are down."""
        app_with_middleware.state.db_ready = False
        app_with_middleware.state.redis_ready = False

        client = TestClient(app_with_middleware)
        response = client.get("/livez")

        assert response.status_code == 200

    def test_root_endpoint_always_accessible(self, app_with_middleware):
        """Test that / endpoint works even when services are down."""
        app_with_middleware.state.db_ready = False
        app_with_middleware.state.redis_ready = False

        client = TestClient(app_with_middleware)
        response = client.get("/")

        assert response.status_code == 200

    def test_docs_endpoint_always_accessible(self, app_with_middleware):
        """Test that /docs endpoint works even when services are down."""
        app_with_middleware.state.db_ready = False
        app_with_middleware.state.redis_ready = False

        client = TestClient(app_with_middleware)
        response = client.get("/docs")

        assert response.status_code == 200

    def test_api_endpoint_requires_db(self, app_with_middleware):
        """Test that API endpoints return 503 when DB is down."""
        app_with_middleware.state.db_ready = False
        app_with_middleware.state.db_error = "Connection refused"

        client = TestClient(app_with_middleware)
        response = client.get("/api/test")

        assert response.status_code == 503
        assert "Database connection not available" in response.json()["detail"]
        assert "Connection refused" in response.json()["detail"]

    def test_api_endpoint_requires_redis(self, app_with_middleware):
        """Test that API endpoints return 503 when Redis is down."""
        app_with_middleware.state.db_ready = True
        app_with_middleware.state.redis_ready = False
        app_with_middleware.state.redis_error = "Redis timeout"

        client = TestClient(app_with_middleware)
        response = client.get("/api/test")

        assert response.status_code == 503
        assert "Redis connection not available" in response.json()["detail"]
        assert "Redis timeout" in response.json()["detail"]

    def test_api_endpoint_works_when_services_ready(self, app_with_middleware):
        """Test that API endpoints work when all services are ready."""
        app_with_middleware.state.db_ready = True
        app_with_middleware.state.redis_ready = True

        client = TestClient(app_with_middleware)
        response = client.get("/api/test")

        assert response.status_code == 200
        assert response.json() == {"data": "test"}

    def test_db_checked_before_redis(self, app_with_middleware):
        """Test that DB is checked before Redis."""
        app_with_middleware.state.db_ready = False
        app_with_middleware.state.db_error = "DB error"
        app_with_middleware.state.redis_ready = False
        app_with_middleware.state.redis_error = "Redis error"

        client = TestClient(app_with_middleware)
        response = client.get("/api/test")

        # Should return DB error, not Redis error
        assert response.status_code == 503
        assert "Database" in response.json()["detail"]
