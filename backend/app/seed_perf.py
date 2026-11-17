import asyncio
import hashlib
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Usuario
from app.modules.auth.security import hash_password
from app.modules.deliverables.enums import (
    DeliverableStatus,
    ForumMessageType,
    ReviewDecision,
)
from app.modules.deliverables.models import Comentario, Entrega, Entregable, Revision
from app.modules.projects.enums import (
    MilestoneStatus,
    ParticipantRole,
    ProjectStatus,
    ProjectType,
)
from app.modules.projects.models import Hito, Participacion, Proyecto
from app.modules.storage.models import Archivo

PROFESSOR_COUNT = 146
STUDENT_COUNT = 529
PROJECT_COUNT = 529
MILESTONES_PER_PROJECT = 5
DELIVERABLES_PER_PROJECT = 10
PERF_PASSWORD = "Rendimiento123!"
CHUNK_SIZE = 500

DELIVERABLE_PATTERN: list[tuple[DeliverableStatus, int]] = [
    (DeliverableStatus.APPROVED, 2),
    (DeliverableStatus.SUBMITTED, 3),
    (DeliverableStatus.CHANGES_REQUESTED, 2),
    (DeliverableStatus.APPROVED, 3),
    (DeliverableStatus.APPROVED, 2),
    (DeliverableStatus.SUBMITTED, 3),
    (DeliverableStatus.CHANGES_REQUESTED, 2),
    (DeliverableStatus.APPROVED, 3),
    (DeliverableStatus.APPROVED, 2),
    (DeliverableStatus.SUBMITTED, 3),
]


def _chunks(rows: list[dict[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    for start in range(0, len(rows), CHUNK_SIZE):
        yield rows[start : start + CHUNK_SIZE]


async def _bulk_insert(
    db: AsyncSession,
    model: Any,
    rows: list[dict[str, Any]],
) -> None:
    for chunk in _chunks(rows):
        await db.execute(insert(model), chunk)
    await db.commit()


def _create_sparse_file(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.truncate(size)


async def _ensure_empty_database(db: AsyncSession) -> None:
    count = await db.scalar(select(func.count()).select_from(Usuario))
    if count:
        raise SystemExit(
            "La base de rendimiento ya contiene usuarios. "
            "Reinicie el stack de rendimiento antes de sembrar."
        )


async def seed() -> None:
    """Genera el escenario SRS completo para pruebas de rendimiento."""
    if settings.app_env != "perf" or "perf" not in settings.database_url:
        raise SystemExit(
            "seed_perf solo se ejecuta con APP_ENV=perf y una base de datos perf."
        )

    now = datetime.now(UTC)
    today = date.today()
    password_hash = hash_password(PERF_PASSWORD)

    async with SessionLocal() as db:
        await _ensure_empty_database(db)

        user_rows: list[dict[str, Any]] = []
        professor_ids: list[uuid.UUID] = []
        student_ids: list[uuid.UUID] = []

        for index in range(PROFESSOR_COUNT):
            user_id = uuid.uuid4()
            professor_ids.append(user_id)
            user_rows.append(
                {
                    "id": user_id,
                    "nombre": f"Profesor {index + 1}",
                    "correo": f"profe{index + 1:04d}@perf.example.com",
                    "tipo": UserType.PROFESSOR,
                    "credencial": password_hash,
                    "estado": UserStatus.ACTIVE,
                    "consentimiento_fecha": now,
                    "consentimiento_version": "perf",
                }
            )

        for index in range(STUDENT_COUNT):
            user_id = uuid.uuid4()
            student_ids.append(user_id)
            user_rows.append(
                {
                    "id": user_id,
                    "nombre": f"Estudiante {index + 1}",
                    "correo": f"est{index + 1:04d}@perf.example.com",
                    "tipo": UserType.STUDENT,
                    "credencial": password_hash,
                    "estado": UserStatus.ACTIVE,
                    "consentimiento_fecha": now,
                    "consentimiento_version": "perf",
                }
            )

        await _bulk_insert(db, Usuario, user_rows)

        project_rows: list[dict[str, Any]] = []
        participation_rows: list[dict[str, Any]] = []
        milestone_rows: list[dict[str, Any]] = []
        deliverable_rows: list[dict[str, Any]] = []
        submission_rows: list[dict[str, Any]] = []
        review_rows: list[dict[str, Any]] = []
        comment_rows: list[dict[str, Any]] = []
        file_rows: list[dict[str, Any]] = []
        apparent_file_bytes = 0

        project_types = [
            ProjectType.MEMOIR,
            ProjectType.THESIS,
            ProjectType.RESEARCH,
        ]

        for project_index in range(PROJECT_COUNT):
            project_id = uuid.uuid4()
            manager_id = professor_ids[project_index % PROFESSOR_COUNT]
            collaborator_ids = [
                student_ids[(project_index * 2) % STUDENT_COUNT],
                student_ids[(project_index * 2 + 1) % STUDENT_COUNT],
            ]
            active = project_index < 265
            project_rows.append(
                {
                    "id": project_id,
                    "tipo": project_types[project_index % len(project_types)],
                    "tema": f"Proyecto de rendimiento {project_index + 1:04d}",
                    "estado": (
                        ProjectStatus.ACTIVE if active else ProjectStatus.CLOSED
                    ),
                    "fecha_inicio": today - timedelta(days=120),
                    "fecha_cierre": None if active else today - timedelta(days=10),
                    "fecha_ultima_modificacion": now - timedelta(minutes=project_index),
                }
            )
            participation_rows.extend(
                [
                    {
                        "usuario_id": manager_id,
                        "proyecto_id": project_id,
                        "rol": ParticipantRole.MANAGER,
                        "fecha_alta": now - timedelta(days=100),
                    },
                    {
                        "usuario_id": collaborator_ids[0],
                        "proyecto_id": project_id,
                        "rol": ParticipantRole.COLLABORATOR,
                        "fecha_alta": now - timedelta(days=100),
                    },
                    {
                        "usuario_id": collaborator_ids[1],
                        "proyecto_id": project_id,
                        "rol": ParticipantRole.COLLABORATOR,
                        "fecha_alta": now - timedelta(days=100),
                    },
                ]
            )

            milestone_ids: list[uuid.UUID] = []
            for milestone_index in range(1, MILESTONES_PER_PROJECT + 1):
                milestone_id = uuid.uuid4()
                milestone_ids.append(milestone_id)
                milestone_rows.append(
                    {
                        "id": milestone_id,
                        "proyecto_id": project_id,
                        "nombre": f"Hito {milestone_index}",
                        "orden": milestone_index,
                        "estado": MilestoneStatus.PENDING,
                    }
                )

            for deliverable_index in range(DELIVERABLES_PER_PROJECT):
                state, version_count = DELIVERABLE_PATTERN[deliverable_index]
                deliverable_id = uuid.uuid4()
                milestone_id = milestone_ids[deliverable_index % MILESTONES_PER_PROJECT]
                deadline = now + timedelta(days=(deliverable_index + 1) * 5)
                deliverable_rows.append(
                    {
                        "id": deliverable_id,
                        "hito_id": milestone_id,
                        "titulo": f"Entregable {deliverable_index + 1}",
                        "descripcion": (
                            "Entregable sintético para pruebas de rendimiento."
                        ),
                        "fecha_limite": deadline,
                        "formatos_admitidos": ["pdf", "zip"],
                        "tamano_max_mb": 50,
                        "estado": state,
                    }
                )

                for version in range(1, version_count + 1):
                    submission_id = uuid.uuid4()
                    submitted_at = deadline - timedelta(
                        days=version_count - version + 1
                    )
                    submission_rows.append(
                        {
                            "id": submission_id,
                            "entregable_id": deliverable_id,
                            "version": version,
                            "autor_id": collaborator_ids[0],
                            "fecha_envio": submitted_at,
                            "enlace": (
                                f"https://example.com/perf/{project_id}/"
                                f"{deliverable_id}/v{version}"
                            ),
                        }
                    )

                    if (project_index + deliverable_index + version) % 2 == 0:
                        size = 5_000_000 + (
                            (project_index * 31 + deliverable_index * 17 + version * 7)
                            % 5_000_000
                        )
                        key = f"perf/{project_id}/{deliverable_id}/v{version}.pdf"
                        file_rows.append(
                            {
                                "id": uuid.uuid4(),
                                "entrega_id": submission_id,
                                "nombre": f"v{version}.pdf",
                                "tipo_mime": "application/pdf",
                                "tamano": size,
                                "clave_almacenamiento": key,
                                "sha256": hashlib.sha256(
                                    key.encode("utf-8")
                                ).hexdigest(),
                            }
                        )
                        apparent_file_bytes += size
                        _create_sparse_file(Path(settings.upload_dir) / key, size)

                    reviewed = state != DeliverableStatus.SUBMITTED or (
                        version < version_count
                    )
                    if reviewed:
                        decision = (
                            ReviewDecision.CHANGES_REQUESTED
                            if state == DeliverableStatus.CHANGES_REQUESTED
                            else ReviewDecision.APPROVED
                        )
                        review_rows.append(
                            {
                                "id": uuid.uuid4(),
                                "entrega_id": submission_id,
                                "gestor_id": manager_id,
                                "decision": decision,
                                "fecha": submitted_at + timedelta(hours=12),
                            }
                        )

                comment_rows.append(
                    {
                        "id": uuid.uuid4(),
                        "entregable_id": deliverable_id,
                        "autor_id": None,
                        "tipo": ForumMessageType.SYSTEM,
                        "texto": "Sistema: entregable creado.",
                        "fecha": now - timedelta(days=30),
                    }
                )
                comment_rows.append(
                    {
                        "id": uuid.uuid4(),
                        "entregable_id": deliverable_id,
                        "autor_id": collaborator_ids[1],
                        "tipo": ForumMessageType.USER,
                        "texto": "Comentario sintético de rendimiento.",
                        "fecha": now - timedelta(days=20),
                    }
                )

        await _bulk_insert(db, Proyecto, project_rows)
        await _bulk_insert(db, Participacion, participation_rows)
        await _bulk_insert(db, Hito, milestone_rows)
        await _bulk_insert(db, Entregable, deliverable_rows)
        await _bulk_insert(db, Entrega, submission_rows)
        await _bulk_insert(db, Revision, review_rows)
        await _bulk_insert(db, Comentario, comment_rows)
        await _bulk_insert(db, Archivo, file_rows)

    print(
        "Perf seed completado: "
        f"{PROFESSOR_COUNT + STUDENT_COUNT} cuentas, "
        f"{PROJECT_COUNT} proyectos, {len(milestone_rows)} hitos, "
        f"{len(deliverable_rows)} entregables, {len(submission_rows)} entregas, "
        f"{len(review_rows)} revisiones, {len(file_rows)} archivos."
    )
    print(f"Bytes aparentes de archivos: {apparent_file_bytes}")
    print(f"Contraseña de rendimiento: {PERF_PASSWORD}")
    print("Profesor de prueba: profe0001@perf.example.com")
    print("Estudiante de prueba: est0001@perf.example.com")


if __name__ == "__main__":
    asyncio.run(seed())
