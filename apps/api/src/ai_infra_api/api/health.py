from typing import Literal

from fastapi import APIRouter, Request, Response
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ai_infra_api.db.session import Database
from ai_infra_api.schemas.health import DependencyStatus, LivenessResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LivenessResponse)
async def live(request: Request) -> LivenessResponse:
    return LivenessResponse(version=request.app.state.settings.app_version)


@router.get("/health/ready", response_model=ReadinessResponse, status_code=200)
async def ready(request: Request, response: Response) -> ReadinessResponse:
    statuses: dict[str, DependencyStatus] = {}
    database: Database = request.app.state.database
    redis: Redis = request.app.state.redis

    try:
        async with database.session_factory() as session:
            db_session: AsyncSession = session
            await db_session.execute(text("SELECT 1"))
        statuses["database"] = DependencyStatus(status="ready")
    except Exception:
        statuses["database"] = DependencyStatus(
            status="unavailable", detail="Database connection failed."
        )

    try:
        await redis.ping()
        statuses["redis"] = DependencyStatus(status="ready")
    except Exception:
        statuses["redis"] = DependencyStatus(
            status="unavailable", detail="Redis connection failed."
        )

    overall: Literal["ready", "degraded"] = (
        "ready" if all(item.status == "ready" for item in statuses.values()) else "degraded"
    )
    if overall == "degraded":
        response.status_code = 503
    return ReadinessResponse(status=overall, dependencies=statuses)
