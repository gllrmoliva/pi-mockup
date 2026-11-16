import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Notificacion(TimestampMixin, Base):
    """Registro de un aviso enviado o pendiente de envío."""

    __tablename__ = "notificacion"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    destinatario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo_evento: Mapped[str] = mapped_column(String(100), nullable=False)
    referencia_entidad: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_notificacion_destinatario_id_fecha_envio",
            "destinatario_id",
            "fecha_envio",
        ),
    )


__all__ = ["Notificacion"]
