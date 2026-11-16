import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import pg_enum
from app.modules.auth.enums import UserStatus, UserType

USER_TYPE_ENUM = pg_enum(UserType, "user_type")
USER_STATUS_ENUM = pg_enum(UserStatus, "user_status")


class Usuario(TimestampMixin, Base):
    """Cuenta de profesor o estudiante."""

    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    correo: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    tipo: Mapped[UserType] = mapped_column(USER_TYPE_ENUM, nullable=False)
    credencial: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[UserStatus] = mapped_column(
        USER_STATUS_ENUM,
        nullable=False,
        default=UserStatus.INVITED,
        server_default=text("'invitada'"),
    )
    consentimiento_fecha: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consentimiento_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Sesion(TimestampMixin, Base):
    """Sesión opaca asociada a una cookie HttpOnly."""

    __tablename__ = "sesion"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    fecha_expiracion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


__all__ = ["Sesion", "Usuario"]
