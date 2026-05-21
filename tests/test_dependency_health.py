from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.main import app


client = TestClient(app)


class FakeRedis:
    def ping(self) -> bool:
        return True


def test_dependency_health_check(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.health.get_redis_client", lambda: FakeRedis())

    response = client.get("/health/dependencies")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "redis": "ok",
    }


def test_dependency_health_check_returns_503_when_redis_fails(monkeypatch) -> None:
    class BrokenRedis:
        def ping(self) -> bool:
            raise RedisError("redis down")

    monkeypatch.setattr("app.api.routes.health.get_redis_client", lambda: BrokenRedis())

    response = client.get("/health/dependencies")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "degraded",
        "database": "ok",
        "redis": "unavailable",
    }
