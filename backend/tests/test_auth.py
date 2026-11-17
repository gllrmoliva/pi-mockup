from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Sesion, Usuario
from app.modules.auth.security import (
    hash_password,
    hash_session_token,
    verify_password,
)

PASSWORD = "TestPassword123!"
INVALID_CREDENTIALS = "Correo o contraseña incorrectos."


async def create_user(
    email: str,
    *,
    status: UserStatus = UserStatus.ACTIVE,
    user_type: UserType = UserType.PROFESSOR,
) -> Usuario:
    async with SessionLocal() as db:
        user = Usuario(
            nombre="Test User",
            correo=email.lower(),
            tipo=user_type,
            credencial=hash_password(PASSWORD),
            estado=status,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def test_login_success_sets_http_only_cookie(
    client: AsyncClient,
) -> None:
    await create_user("professor@example.com")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "PROFESSOR@example.com", "password": PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "professor@example.com"
    assert body["user"]["user_type"] == "professor"
    assert body["user"]["state"] == "active"

    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "hito_session=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "professor@example.com"


async def test_invalid_password_is_rejected(client: AsyncClient) -> None:
    await create_user("professor@example.com")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "professor@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == INVALID_CREDENTIALS


async def test_empty_credentials_are_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "", "password": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Correo y/o contraseña vacíos."


async def test_invalid_email_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == INVALID_CREDENTIALS


async def test_inactive_account_is_rejected(client: AsyncClient) -> None:
    await create_user("inactive@example.com", status=UserStatus.INVITED)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == INVALID_CREDENTIALS


async def test_me_requires_a_session(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_logout_revokes_the_session(client: AsyncClient) -> None:
    await create_user("professor@example.com")
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "professor@example.com", "password": PASSWORD},
    )
    assert login.status_code == 200

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401


async def test_passwords_and_session_tokens_are_hashed(
    client: AsyncClient,
) -> None:
    await create_user("professor@example.com")

    async with SessionLocal() as db:
        stored_user = await db.scalar(
            select(Usuario).where(Usuario.correo == "professor@example.com")
        )
        assert stored_user is not None
        assert stored_user.credencial != PASSWORD
        assert verify_password(PASSWORD, stored_user.credencial)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "professor@example.com", "password": PASSWORD},
    )
    assert login.status_code == 200

    token = client.cookies.get("hito_session")
    assert token is not None
    assert token != hash_session_token(token)

    async with SessionLocal() as db:
        stored_session = await db.scalar(
            select(Sesion).where(Sesion.token_hash == hash_session_token(token))
        )
        assert stored_session is not None


async def test_expired_session_is_rejected(client: AsyncClient) -> None:
    user = await create_user("professor@example.com")
    token = "expired-token"

    async with SessionLocal() as db:
        db.add(
            Sesion(
                usuario_id=user.id,
                token_hash=hash_session_token(token),
                fecha_expiracion=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        await db.commit()

    client.cookies.set("hito_session", token)
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def failed_login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_five_failed_logins_lock_account(client: AsyncClient) -> None:
    user = await create_user("locked@example.com")

    for _ in range(settings.max_failed_login_attempts):
        await failed_login(client, user.correo)

    async with SessionLocal() as db:
        stored_user = await db.scalar(select(Usuario).where(Usuario.id == user.id))
        assert stored_user is not None
        assert stored_user.intentos_fallidos == settings.max_failed_login_attempts
        assert stored_user.bloqueado_hasta is not None
        remaining = stored_user.bloqueado_hasta - datetime.now(UTC)
        assert timedelta(minutes=settings.login_lockout_minutes - 1) < remaining
        assert remaining <= timedelta(minutes=settings.login_lockout_minutes)

    locked = await client.post(
        "/api/v1/auth/login",
        json={"email": user.correo, "password": PASSWORD},
    )

    assert locked.status_code == 423
    assert locked.json()["error"]["code"] == "ACCOUNT_LOCKED"
    assert locked.json()["error"]["message"] == (
        "Cuenta bloqueada temporalmente. "
        f"Intente nuevamente en {settings.login_lockout_minutes} minutos."
    )
    assert locked.headers.get("set-cookie") is None


async def test_expired_lock_allows_login_and_resets_counter(
    client: AsyncClient,
) -> None:
    user = await create_user("expired-lock@example.com")

    async with SessionLocal() as db:
        stored_user = await db.scalar(select(Usuario).where(Usuario.id == user.id))
        assert stored_user is not None
        stored_user.intentos_fallidos = settings.max_failed_login_attempts
        stored_user.bloqueado_hasta = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.correo, "password": PASSWORD},
    )

    assert response.status_code == 200
    async with SessionLocal() as db:
        stored_user = await db.scalar(select(Usuario).where(Usuario.id == user.id))
        assert stored_user is not None
        assert stored_user.intentos_fallidos == 0
        assert stored_user.bloqueado_hasta is None


async def test_successful_login_resets_failed_attempts(client: AsyncClient) -> None:
    user = await create_user("reset@example.com")

    await failed_login(client, user.correo)
    await failed_login(client, user.correo)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.correo, "password": PASSWORD},
    )

    assert response.status_code == 200
    async with SessionLocal() as db:
        stored_user = await db.scalar(select(Usuario).where(Usuario.id == user.id))
        assert stored_user is not None
        assert stored_user.intentos_fallidos == 0
        assert stored_user.bloqueado_hasta is None


async def test_unknown_email_is_not_locked(client: AsyncClient) -> None:
    for _ in range(settings.max_failed_login_attempts + 1):
        await failed_login(client, "ghost@example.com")

    async with SessionLocal() as db:
        stored_user = await db.scalar(
            select(Usuario).where(Usuario.correo == "ghost@example.com")
        )
        assert stored_user is None


async def test_stored_passwords_use_argon2id(client: AsyncClient) -> None:
    await create_user("hash@example.com")

    async with SessionLocal() as db:
        stored_user = await db.scalar(
            select(Usuario).where(Usuario.correo == "hash@example.com")
        )
        assert stored_user is not None
        assert stored_user.credencial.startswith("$argon2id$")


async def test_auth_routes_do_not_include_registration() -> None:
    auth_paths = {
        path for path in app.openapi()["paths"] if path.startswith("/api/v1/auth")
    }

    assert auth_paths == {
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
    }
