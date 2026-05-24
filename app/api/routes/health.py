from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.cache.redis import get_redis_client
from app.core.config import get_settings
from app.db.session import get_db


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": settings.api_version,
    }


@router.get("/dependencies")
def dependency_health_check(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    statuses = {
        "database": "ok",
        "redis": "ok",
    }

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        statuses["database"] = "unavailable"

    try:
        redis_client = get_redis_client()
        redis_client.ping()
    except RedisError:
        statuses["redis"] = "unavailable"

    if any(status != "ok" for status in statuses.values()):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                **statuses,
            },
        )

    return {
        "status": "ok",
        **statuses,
    }
