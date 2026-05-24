from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    settings = get_settings()
    assert response.json() == {
        "status": "ok",
        "environment": settings.environment,
        "version": settings.api_version,
    }


def test_root_route() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Investment Research System" in response.text
