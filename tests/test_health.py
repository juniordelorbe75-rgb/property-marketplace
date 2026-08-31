import os

# backend.db requires DATABASE_URL while the application is imported.
# SQLite keeps these smoke tests isolated from the developer PostgreSQL database.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_property_marketplace.db")

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("x-request-id")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_readiness_check():
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
    }


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Property Marketplace API is running"
    }
