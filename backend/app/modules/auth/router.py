from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.audit.service import record_audit
from app.core.http import get_client_ip
from app.db.session import get_db
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    UserResponse,
    user_to_response,
)
from app.modules.auth.security import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
)
from app.modules.auth.service import (
    authenticate_user,
    create_session,
    delete_session,
    get_user_for_session,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """Inicia sesión con correo y contraseña."""
    user = await authenticate_user(db, payload.email, payload.password)
    token, session = await create_session(db, user)
    await record_audit(
        db,
        user_id=user.id,
        action="sesion.iniciar",
        entity="sesion",
        entity_id=session.id,
        ip=get_client_ip(request),
    )
    await db.commit()
    set_session_cookie(response, token)
    return LoginResponse(user=user_to_response(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Cierra la sesión actual y elimina la cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is not None:
        user = await get_user_for_session(db, token)
        session = await delete_session(db, token)
        if user is not None and session is not None:
            await record_audit(
                db,
                user_id=user.id,
                action="sesion.cerrar",
                entity="sesion",
                entity_id=session.id,
                ip=get_client_ip(request),
            )
        await db.commit()
    clear_session_cookie(response)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> UserResponse:
    """Devuelve la cuenta autenticada."""
    return user_to_response(current_user)
