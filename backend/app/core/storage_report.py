import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.storage.models import Archivo

GIB = 1024**3
DEFAULT_QUOTA_GB = 100.0
DEFAULT_ALERT_PERCENT = 80.0
DISCREPANCY_ALERT_PERCENT = 5.0

StorageStatus = Literal["ok", "warning", "critical"]


@dataclass(frozen=True)
class StorageReport:
    """Resultado del reporte de almacenamiento."""

    actual_bytes: int
    reported_bytes: int
    quota_gb: float
    alert_percent: float
    usage_percent: float
    discrepancy_percent: float
    status: StorageStatus
    exit_code: int
    warnings: tuple[str, ...]


def directory_size(path: Path) -> int:
    """Suma el tamaño aparente de los archivos bajo un directorio."""
    if not path.exists():
        return 0

    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


async def reported_storage_bytes(db: AsyncSession) -> int:
    """Suma los tamaños registrados en la tabla de archivos."""
    result = await db.scalar(select(func.coalesce(func.sum(Archivo.tamano), 0)))
    return int(result or 0)


def evaluate_storage(
    actual_bytes: int,
    reported_bytes: int,
    *,
    quota_gb: float = DEFAULT_QUOTA_GB,
    alert_percent: float = DEFAULT_ALERT_PERCENT,
) -> StorageReport:
    """Evalúa el uso y la consistencia del almacenamiento."""
    if quota_gb <= 0:
        raise ValueError("La cuota debe ser mayor que cero.")
    if not 0 <= alert_percent <= 100:
        raise ValueError("El porcentaje de alerta debe estar entre 0 y 100.")

    quota_bytes = int(quota_gb * GIB)
    usage_basis = max(actual_bytes, reported_bytes)
    usage_percent_raw = usage_basis / quota_bytes * 100
    discrepancy_raw = (
        abs(actual_bytes - reported_bytes) / max(actual_bytes, reported_bytes, 1) * 100
    )
    usage_percent = round(usage_percent_raw, 2)
    discrepancy_percent = round(discrepancy_raw, 2)

    status: StorageStatus = "ok"
    exit_code = 0
    warnings: list[str] = []

    if usage_percent_raw >= 100:
        status = "critical"
        exit_code = 1
        warnings.append(
            f"Uso de almacenamiento en {usage_percent:.2f} %; se alcanzó la cuota."
        )
    elif usage_percent_raw >= alert_percent:
        status = "warning"
        exit_code = 2
        warnings.append(
            f"Uso de almacenamiento en {usage_percent:.2f} %; "
            f"supera el umbral de alerta de {alert_percent:.2f} %."
        )

    if discrepancy_raw > DISCREPANCY_ALERT_PERCENT:
        if status != "critical":
            status = "warning"
            exit_code = 2
        warnings.append(
            f"Diferencia entre bytes reales y metadatos: {discrepancy_percent:.2f} %."
        )

    return StorageReport(
        actual_bytes=actual_bytes,
        reported_bytes=reported_bytes,
        quota_gb=quota_gb,
        alert_percent=alert_percent,
        usage_percent=usage_percent,
        discrepancy_percent=discrepancy_percent,
        status=status,
        exit_code=exit_code,
        warnings=tuple(warnings),
    )


async def build_report(
    upload_dir: Path,
    *,
    quota_gb: float = DEFAULT_QUOTA_GB,
    alert_percent: float = DEFAULT_ALERT_PERCENT,
) -> StorageReport:
    """Calcula el reporte con el volumen local y la base de datos."""
    actual_bytes = directory_size(upload_dir)
    async with SessionLocal() as db:
        reported_bytes = await reported_storage_bytes(db)
    return evaluate_storage(
        actual_bytes,
        reported_bytes,
        quota_gb=quota_gb,
        alert_percent=alert_percent,
    )


def report_to_dict(report: StorageReport) -> dict[str, Any]:
    """Convierte el reporte a un diccionario serializable."""
    return asdict(report)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reporta el uso de almacenamiento y su consistencia."
    )
    parser.add_argument(
        "--upload-dir",
        default=settings.upload_dir,
        help="Directorio de archivos subidos.",
    )
    parser.add_argument(
        "--quota-gb",
        type=float,
        default=DEFAULT_QUOTA_GB,
        help="Cuota de almacenamiento en GB.",
    )
    parser.add_argument(
        "--alert-percent",
        type=float,
        default=DEFAULT_ALERT_PERCENT,
        help="Porcentaje de uso que genera una advertencia.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Archivo JSON de salida; si se omite, imprime en stdout.",
    )
    return parser.parse_args(argv)


async def _build_report_from_args(args: argparse.Namespace) -> StorageReport:
    return await build_report(
        Path(args.upload_dir),
        quota_gb=args.quota_gb,
        alert_percent=args.alert_percent,
    )


def main() -> None:
    """Ejecuta el reporte de almacenamiento desde la línea de comandos."""
    args = _parse_args()
    report = asyncio.run(_build_report_from_args(args))
    payload = json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    sys.exit(report.exit_code)


if __name__ == "__main__":
    main()
