from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_web_ui_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Investment Research System" in response.text


def test_web_static_asset() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "graph/research" in response.text
