from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/meta")
async def meta() -> dict[str, str]:
    """Expone metadatos básicos de la aplicación."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }
