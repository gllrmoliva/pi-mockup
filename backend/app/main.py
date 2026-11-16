from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import configure_logging
from app.db.session import engine

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_exception_handler(AppError, app_error_handler)
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(api_router, prefix="/api/v1")
