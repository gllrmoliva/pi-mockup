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
LOCKED_ACCOUNT_MESSAGE = "Cuenta bloqueada temporalmente."


def locked_account_message() -> str:
    """Construye el mensaje de bloqueo con la duración configurada."""
    minutes = settings.login_lockout_minutes
    return f"{LOCKED_ACCOUNT_MESSAGE} Intente nuevamente en {minutes} minutos."


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
        select(Usuario)
        .where(Usuario.correo == normalize_email(email))
        .with_for_update()
    )
    if user is None:
        raise AppError("INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE, 401)

    now = datetime.now(UTC)
    if user.bloqueado_hasta is not None:
        if user.bloqueado_hasta > now:
            raise AppError("ACCOUNT_LOCKED", locked_account_message(), 423)
        user.bloqueado_hasta = None
        user.intentos_fallidos = 0

    try:
        password_matches = verify_password(password, user.credencial)
    except Exception:
        logger.exception("Stored credential could not be verified")
        password_matches = False

    if not password_matches:
        user.intentos_fallidos += 1
        if user.intentos_fallidos >= settings.max_failed_login_attempts:
            user.bloqueado_hasta = now + timedelta(
                minutes=settings.login_lockout_minutes
            )
        await db.commit()
        raise AppError("INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE, 401)

    if user.estado != UserStatus.ACTIVE:
        await db.commit()
        raise AppError("INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE, 401)

    user.intentos_fallidos = 0
    user.bloqueado_hasta = None
    await db.commit()
    return user


async def create_session(db: AsyncSession, user: Usuario) -> tuple[str, Sesion]:
    """Crea una sesión opaca y devuelve el token y la sesión persistida."""
    now = datetime.now(UTC)
    token = generate_session_token()
    session = Sesion(
        usuario_id=user.id,
        token_hash=hash_session_token(token),
        fecha_expiracion=now + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    await db.execute(delete(Sesion).where(Sesion.fecha_expiracion <= now))
    await db.commit()
    return token, session


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


async def delete_session(db: AsyncSession, token: str) -> Sesion | None:
    """Elimina la sesión asociada al token y la devuelve para auditarla."""
    session = await db.scalar(
        select(Sesion).where(Sesion.token_hash == hash_session_token(token))
    )
    if session is None:
        return None
    await db.delete(session)
    return session
