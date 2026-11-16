from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.session import get_db
from app.modules.auth.models import Usuario
from app.modules.auth.security import SESSION_COOKIE_NAME
from app.modules.auth.service import get_user_for_session

UNAUTHENTICATED_MESSAGE = "Tu sesión expiró o no es válida."


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Resuelve la cuenta autenticada a partir de la cookie de sesión."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise AppError("UNAUTHENTICATED", UNAUTHENTICATED_MESSAGE, 401)

    user = await get_user_for_session(db, token)
    if user is None:
        raise AppError("UNAUTHENTICATED", UNAUTHENTICATED_MESSAGE, 401)

    return user
