import argparse
import asyncio
from datetime import datetime

from app.core.audit.service import purge_audit_logs
from app.db.session import SessionLocal


def _parse_now(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("La fecha debe incluir zona horaria.")
    return parsed


async def _run(now: datetime | None) -> None:
    async with SessionLocal() as db:
        ips, rows = await purge_audit_logs(db, now=now)
    print(f"IPs anonimizadas: {ips}; filas eliminadas: {rows}")


def main() -> None:
    """Ejecuta la limpieza de auditoría desde la línea de comandos."""
    parser = argparse.ArgumentParser(description="Purga la auditoría vencida.")
    parser.add_argument(
        "--now",
        type=_parse_now,
        default=None,
        help="Fecha de referencia ISO 8601 con zona horaria.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.now))


if __name__ == "__main__":
    main()
