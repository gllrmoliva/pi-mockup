import hashlib
import secrets

from fastapi import Response
from pwdlib import PasswordHash

from app.core.config import settings

SESSION_COOKIE_NAME = "hito_session"
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Genera un hash Argon2id para una contraseña."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash almacenado."""
    return _password_hash.verify(password, password_hash)


def generate_session_token() -> str:
    """Genera un token opaco de sesión."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Calcula el hash SHA-256 que se persiste de un token de sesión."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_session_cookie(response: Response, token: str) -> None:
    """Escribe la cookie HttpOnly de sesión."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Elimina la cookie de sesión."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
