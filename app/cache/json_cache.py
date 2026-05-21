import json
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.cache.redis_client import get_redis_client


class JsonCache:
    def __init__(self, redis_client: Redis | None = None) -> None:
        self.redis_client = redis_client or get_redis_client()

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            value = self.redis_client.get(key)
        except RedisError:
            return None

        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        try:
            self.redis_client.setex(key, ttl_seconds, json.dumps(value))
        except RedisError:
            return


def get_json_cache() -> JsonCache:
    return JsonCache()
