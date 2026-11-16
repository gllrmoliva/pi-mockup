import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import pg_enum
from app.modules.deliverables.enums import DeliverableStatus, ReviewDecision

DELIVERABLE_STATUS_ENUM = pg_enum(DeliverableStatus, "deliverable_status")
REVIEW_DECISION_ENUM = pg_enum(ReviewDecision, "review_decision")


class Entregable(TimestampMixin, Base):
    """Requisito con fecha límite dentro de un hito."""

    __tablename__ = "entregable"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hito_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hito.id", ondelete="CASCADE"),
        nullable=False,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_limite: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    formatos_admitidos: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    tamano_max_mb: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50, server_default=text("50")
    )
    estado: Mapped[DeliverableStatus] = mapped_column(
        DELIVERABLE_STATUS_ENUM,
        nullable=False,
        default=DeliverableStatus.PENDING,
        server_default=text("'pendiente'"),
    )

    __table_args__ = (
        Index(
            "ix_entregable_hito_id_fecha_limite_created_at",
            "hito_id",
            "fecha_limite",
            "created_at",
        ),
    )


class Entrega(TimestampMixin, Base):
    """Versión concreta enviada para un entregable."""

    __tablename__ = "entrega"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entregable_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("entregable.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    autor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    enlace: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    __table_args__ = (
        UniqueConstraint("entregable_id", "version", name="uq_entrega_version"),
    )


class Revision(TimestampMixin, Base):
    """Decisión de un gestor sobre una entrega."""

    __tablename__ = "revision"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entrega_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("entrega.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    gestor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[ReviewDecision] = mapped_column(
        REVIEW_DECISION_ENUM, nullable=False
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Comentario(TimestampMixin, Base):
    """Mensaje del foro de un entregable."""

    __tablename__ = "comentario"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entregable_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("entregable.id", ondelete="CASCADE"),
        nullable=False,
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_comentario_entregable_id_fecha", "entregable_id", "fecha"),
    )


__all__ = ["Comentario", "Entregable", "Entrega", "Revision"]
