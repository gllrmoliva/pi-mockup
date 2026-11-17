from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit.models import RegistroAuditoria

IP_RETENTION_DAYS = 90
ROW_RETENTION_DAYS = 365


async def record_audit(
    db: AsyncSession,
    *,
    user_id: UUID,
    action: str,
    entity: str,
    entity_id: str | UUID,
    ip: str | None,
) -> RegistroAuditoria:
    """Agrega una fila de auditoría; el llamador controla el commit."""
    record = RegistroAuditoria(
        usuario_id=user_id,
        accion=action,
        entidad=entity,
        entidad_id=str(entity_id),
        ip=ip,
    )
    db.add(record)
    return record


async def purge_audit_logs(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> tuple[int, int]:
    """Anonimiza IP antiguas y elimina filas vencidas."""
    reference = now or datetime.now(UTC)
    ip_cutoff = reference - timedelta(days=IP_RETENTION_DAYS)
    row_cutoff = reference - timedelta(days=ROW_RETENTION_DAYS)

    row_result = cast(
        CursorResult[Any],
        await db.execute(
            delete(RegistroAuditoria).where(RegistroAuditoria.fecha < row_cutoff)
        ),
    )
    ip_result = cast(
        CursorResult[Any],
        await db.execute(
            update(RegistroAuditoria)
            .where(
                RegistroAuditoria.fecha < ip_cutoff,
                RegistroAuditoria.ip.is_not(None),
            )
            .values(ip=None)
        ),
    )
    await db.commit()
    return ip_result.rowcount, row_result.rowcount


__all__ = [
    "IP_RETENTION_DAYS",
    "ROW_RETENTION_DAYS",
    "purge_audit_logs",
    "record_audit",
]
