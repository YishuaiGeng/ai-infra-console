import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from ai_infra_api.api.health import router as health_router
from ai_infra_api.api.router import api_router
from ai_infra_api.core.config import Settings, get_settings
from ai_infra_api.core.errors import AppError, ErrorBody, ErrorResponse
from ai_infra_api.core.logging import configure_logging
from ai_infra_api.core.middleware import RequestContextMiddleware, request_id_from
from ai_infra_api.db.session import Database
from ai_infra_api.services.bootstrap import bootstrap_admin

logger = logging.getLogger(__name__)


def error_payload(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id_from(request),
            details=details,
        )
    ).model_dump(mode="json")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(resolved_settings.database_url)
        redis = Redis.from_url(resolved_settings.redis_url, decode_responses=True)
        app.state.settings = resolved_settings
        app.state.database = database
        app.state.redis = redis
        if resolved_settings.bootstrap_admin_password is not None:
            async with database.session_factory() as session:
                await bootstrap_admin(session, resolved_settings)
        yield
        await redis.aclose()
        await database.close()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url="/redoc" if resolved_settings.docs_enabled else None,
        openapi_url="/openapi.json" if resolved_settings.docs_enabled else None,
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health_router)
    app.include_router(api_router, prefix=resolved_settings.api_prefix)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                request,
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                request,
                code="validation_error",
                message="The request is invalid.",
                details=jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                request,
                code="http_error",
                message=str(exc.detail),
            ),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled request error", extra={"event": "request.unhandled_error"})
        return JSONResponse(
            status_code=500,
            content=error_payload(
                request,
                code="internal_error",
                message="An unexpected error occurred.",
            ),
        )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("ai_infra_api.main:app", host="0.0.0.0", port=8000, reload=False)  # noqa: S104
