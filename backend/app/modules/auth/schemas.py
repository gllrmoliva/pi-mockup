from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Usuario

UserTypeApi = Literal["professor", "student"]
UserStatusApi = Literal["invited", "active"]

USER_TYPE_API: dict[UserType, UserTypeApi] = {
    UserType.PROFESSOR: "professor",
    UserType.STUDENT: "student",
}
USER_STATUS_API: dict[UserStatus, UserStatusApi] = {
    UserStatus.INVITED: "invited",
    UserStatus.ACTIVE: "active",
}


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    email: str
    password: str

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    """Datos públicos de una cuenta."""

    id: UUID
    name: str
    email: str
    user_type: UserTypeApi
    state: UserStatusApi


class LoginResponse(BaseModel):
    """Respuesta de un inicio de sesión exitoso."""

    user: UserResponse


def user_to_response(user: Usuario) -> UserResponse:
    """Convierte el modelo de base de datos al contrato público en inglés."""
    return UserResponse(
        id=user.id,
        name=user.nombre,
        email=user.correo,
        user_type=USER_TYPE_API[user.tipo],
        state=USER_STATUS_API[user.estado],
    )
