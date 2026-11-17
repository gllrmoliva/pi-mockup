import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Archivo(TimestampMixin, Base):
    """Metadatos de un archivo asociado a una entrega o a una revisión."""

    __tablename__ = "archivo"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entrega_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("entrega.id", ondelete="CASCADE"),
        nullable=True,
    )
    revision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("revision.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(255), nullable=False)
    tamano: Mapped[int] = mapped_column(BigInteger, nullable=False)
    clave_almacenamiento: Mapped[str] = mapped_column(
        String(512), nullable=False, unique=True
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(entrega_id, revision_id) = 1",
            name="ck_archivo_un_propietario",
        ),
    )


__all__ = ["Archivo"]
