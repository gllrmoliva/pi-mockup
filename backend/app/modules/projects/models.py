import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import pg_enum
from app.modules.projects.enums import (
    MilestoneStatus,
    ParticipantRole,
    ProjectStatus,
    ProjectType,
)

PROJECT_TYPE_ENUM = pg_enum(ProjectType, "project_type")
PROJECT_STATUS_ENUM = pg_enum(ProjectStatus, "project_status")
PARTICIPANT_ROLE_ENUM = pg_enum(ParticipantRole, "participant_role")
MILESTONE_STATUS_ENUM = pg_enum(MilestoneStatus, "milestone_status")


class Proyecto(TimestampMixin, Base):
    """Memoria, tesis o proyecto de investigación."""

    __tablename__ = "proyecto"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tipo: Mapped[ProjectType] = mapped_column(PROJECT_TYPE_ENUM, nullable=False)
    tema: Mapped[str] = mapped_column(String(300), nullable=False)
    estado: Mapped[ProjectStatus] = mapped_column(
        PROJECT_STATUS_ENUM,
        nullable=False,
        default=ProjectStatus.ACTIVE,
        server_default=text("'activo'"),
    )
    fecha_inicio: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    fecha_cierre: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_ultima_modificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    __table_args__ = (Index("ix_proyecto_modified_at", "modified_at"),)


class Participacion(TimestampMixin, Base):
    """Rol de un usuario dentro de un proyecto."""

    __tablename__ = "participacion"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("proyecto.id", ondelete="CASCADE"),
        primary_key=True,
    )
    rol: Mapped[ParticipantRole] = mapped_column(PARTICIPANT_ROLE_ENUM, nullable=False)
    fecha_alta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_participacion_proyecto_id", "proyecto_id"),)


class Plantilla(TimestampMixin, Base):
    """Plantilla de hitos para un tipo de proyecto y carrera."""

    __tablename__ = "plantilla"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_proyecto: Mapped[ProjectType] = mapped_column(
        PROJECT_TYPE_ENUM, nullable=False
    )
    carrera: Mapped[str] = mapped_column(String(200), nullable=False)


class ItemPlantilla(TimestampMixin, Base):
    """Hito incluido en una plantilla."""

    __tablename__ = "item_plantilla"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plantilla_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plantilla.id", ondelete="CASCADE"),
        nullable=False,
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)

    __table_args__ = (
        UniqueConstraint("plantilla_id", "orden", name="uq_item_plantilla_orden"),
    )


class Hito(TimestampMixin, Base):
    """Etapa o punto de control de un proyecto."""

    __tablename__ = "hito"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("proyecto.id", ondelete="CASCADE"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[MilestoneStatus] = mapped_column(
        MILESTONE_STATUS_ENUM,
        nullable=False,
        default=MilestoneStatus.PENDING,
        server_default=text("'pendiente'"),
    )
    fecha_completado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("proyecto_id", "orden", name="uq_hito_proyecto_orden"),
    )


__all__ = [
    "Hito",
    "ItemPlantilla",
    "Participacion",
    "Plantilla",
    "Proyecto",
]
