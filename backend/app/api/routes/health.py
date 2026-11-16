import logging

from fastapi import APIRouter, Response, status

from app.db.session import check_database

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/live")
async def live() -> dict[str, str]:
    """Indica que el proceso de la API está vivo."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, str]:
    """Indica si la API y la base de datos están disponibles."""
    try:
        await check_database()
    except Exception:
        logger.exception("Database readiness check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "unavailable"}

    return {"status": "ok", "database": "ok"}
