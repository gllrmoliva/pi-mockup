import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.modules.auth.enums import UserStatus
from app.modules.auth.models import Sesion, Usuario
from app.modules.auth.security import (
    generate_session_token,
    hash_session_token,
    verify_password,
)

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS_MESSAGE = "Correo o contraseña incorrectos."


def normalize_email(email: str) -> str:
    """Normaliza el correo para compararlo con el valor almacenado."""
    return email.strip().lower()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Usuario:
    """Valida las credenciales y devuelve la cuenta activa."""
    if not email.strip() or not password:
        raise AppError(
            "EMPTY_CREDENTIALS",
            "Correo y/o contraseña vacíos.",
            status_code=422,
        )

    user = await db.scalar(
        select(Usuario).where(Usuario.correo == normalize_email(email))
    )
    if user is None:
        raise AppError("INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE, 401)

    try:
        password_matches = verify_password(password, user.credencial)
    except Exception:
        logger.exception("Stored credential could not be verified")
        password_matches = False

    if not password_matches or user.estado != UserStatus.ACTIVE:
        raise AppError("INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE, 401)

    return user


async def create_session(db: AsyncSession, user: Usuario) -> str:
    """Crea una sesión opaca y devuelve el token que va a la cookie."""
    now = datetime.now(UTC)
    token = generate_session_token()
    db.add(
        Sesion(
            usuario_id=user.id,
            token_hash=hash_session_token(token),
            fecha_expiracion=now + timedelta(hours=settings.session_ttl_hours),
        )
    )
    await db.execute(delete(Sesion).where(Sesion.fecha_expiracion <= now))
    await db.commit()
    return token


async def get_user_for_session(db: AsyncSession, token: str) -> Usuario | None:
    """Busca la cuenta activa asociada a un token de sesión vigente."""
    statement = (
        select(Usuario)
        .join(Sesion, Sesion.usuario_id == Usuario.id)
        .where(
            Sesion.token_hash == hash_session_token(token),
            Sesion.fecha_expiracion > datetime.now(UTC),
            Usuario.estado == UserStatus.ACTIVE,
        )
    )
    return await db.scalar(statement)


async def delete_session(db: AsyncSession, token: str) -> None:
    """Elimina la sesión asociada al token, si existe."""
    await db.execute(
        delete(Sesion).where(Sesion.token_hash == hash_session_token(token))
    )
    await db.commit()
