from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "local",
        "version": "0.1.0",
    }


def test_root_route() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Investment Research System" in response.text
