from redis.exceptions import RedisError

from app.cache.json_cache import JsonCache


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.values[key] = value
        self.ttl[key] = ttl_seconds


class BrokenRedis:
    def get(self, key: str) -> str | None:
        raise RedisError("redis down")

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        raise RedisError("redis down")


def test_json_cache_round_trip() -> None:
    redis = FakeRedis()
    cache = JsonCache(redis)

    cache.set("key", {"ticker": "AAPL", "price": 210.12}, ttl_seconds=60)

    assert cache.get("key") == {"ticker": "AAPL", "price": 210.12}
    assert redis.ttl["key"] == 60


def test_json_cache_degrades_when_redis_fails() -> None:
    cache = JsonCache(BrokenRedis())

    assert cache.get("key") is None
    cache.set("key", {"value": 1}, ttl_seconds=60)
