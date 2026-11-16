import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Usuario
from app.modules.auth.security import hash_password
from app.modules.deliverables.enums import DeliverableStatus
from app.modules.deliverables.models import Entregable
from app.modules.projects.enums import (
    MilestoneStatus,
    ParticipantRole,
    ProjectStatus,
    ProjectType,
)
from app.modules.projects.models import Hito, Participacion, Proyecto

DEMO_PASSWORD = "HitoDemo123!"
DEMO_USERS: list[tuple[str, str, UserType]] = [
    ("Camila Soto", "camila.soto@udec.cl", UserType.PROFESSOR),
    ("Rodrigo Peña", "rodrigo.pena@udec.cl", UserType.PROFESSOR),
    ("Javiera Contreras", "javiera.contreras@udec.cl", UserType.STUDENT),
    ("Benjamín Aravena", "benjamin.aravena@udec.cl", UserType.STUDENT),
    ("Matías Riquelme", "matias.riquelme@udec.cl", UserType.STUDENT),
    ("Fernanda Torres", "fernanda.torres@udec.cl", UserType.STUDENT),
    ("Antonio Skorin", "antonio.skorin@udec.cl", UserType.PROFESSOR),
]


@dataclass(frozen=True)
class DemoProject:
    """Datos de un proyecto de demostración."""

    topic: str
    project_type: ProjectType
    managers: tuple[str, ...]
    collaborators: tuple[str, ...]
    milestones: tuple[str, ...]


@dataclass(frozen=True)
class DemoDeliverable:
    """Entregable de demostración asociado a un hito."""

    project_topic: str
    milestone_name: str
    title: str
    description: str
    deadline_days: int
    formats: tuple[str, ...]


DEMO_PROJECTS: list[DemoProject] = [
    DemoProject(
        topic=(
            "Reconocimiento de gestos para interfaces sin contacto en "
            "laboratorios clínicos"
        ),
        project_type=ProjectType.MEMOIR,
        managers=("camila.soto@udec.cl", "rodrigo.pena@udec.cl"),
        collaborators=("javiera.contreras@udec.cl",),
        milestones=(
            "Propuesta de memoria",
            "Desarrollo y validación",
            "Informe final y defensa",
        ),
    ),
    DemoProject(
        topic="Reconstrucción 3D de sitios patrimoniales con fotogrametría",
        project_type=ProjectType.MEMOIR,
        managers=("camila.soto@udec.cl",),
        collaborators=("benjamin.aravena@udec.cl",),
        milestones=(),
    ),
    DemoProject(
        topic=("Modelos de lenguaje para retroalimentación automática de escritura"),
        project_type=ProjectType.THESIS,
        managers=("camila.soto@udec.cl",),
        collaborators=("matias.riquelme@udec.cl",),
        milestones=("Propuesta de tesis", "Avances y escritura"),
    ),
    DemoProject(
        topic="Verificación formal de protocolos de consenso",
        project_type=ProjectType.THESIS,
        managers=("antonio.skorin@udec.cl",),
        collaborators=("fernanda.torres@udec.cl",),
        milestones=("Definición del problema",),
    ),
]


DEMO_DELIVERABLES: list[DemoDeliverable] = [
    DemoDeliverable(
        project_topic=(
            "Reconocimiento de gestos para interfaces sin contacto en "
            "laboratorios clínicos"
        ),
        milestone_name="Propuesta de memoria",
        title="Anteproyecto",
        description="Propuesta inicial de la memoria de título.",
        deadline_days=7,
        formats=("pdf",),
    ),
    DemoDeliverable(
        project_topic=(
            "Reconocimiento de gestos para interfaces sin contacto en "
            "laboratorios clínicos"
        ),
        milestone_name="Desarrollo y validación",
        title="Informe de avance 1",
        description="Primer informe de avance del trabajo experimental.",
        deadline_days=14,
        formats=("pdf", "zip"),
    ),
    DemoDeliverable(
        project_topic=(
            "Reconocimiento de gestos para interfaces sin contacto en "
            "laboratorios clínicos"
        ),
        milestone_name="Desarrollo y validación",
        title="Prototipo funcional",
        description="Prototipo y evidencia de funcionamiento.",
        deadline_days=21,
        formats=("pdf", "zip"),
    ),
    DemoDeliverable(
        project_topic=(
            "Reconocimiento de gestos para interfaces sin contacto en "
            "laboratorios clínicos"
        ),
        milestone_name="Informe final y defensa",
        title="Informe final",
        description="Versión final de la memoria para revisión y defensa.",
        deadline_days=60,
        formats=("pdf",),
    ),
    DemoDeliverable(
        project_topic=(
            "Modelos de lenguaje para retroalimentación automática de escritura"
        ),
        milestone_name="Propuesta de tesis",
        title="Propuesta de tesis",
        description="Documento de propuesta de la tesis de magíster.",
        deadline_days=15,
        formats=("pdf",),
    ),
    DemoDeliverable(
        project_topic=(
            "Modelos de lenguaje para retroalimentación automática de escritura"
        ),
        milestone_name="Avances y escritura",
        title="Avance 1",
        description="Primer avance del trabajo de tesis.",
        deadline_days=30,
        formats=("pdf", "zip"),
    ),
    DemoDeliverable(
        project_topic="Verificación formal de protocolos de consenso",
        milestone_name="Definición del problema",
        title="Definición del problema",
        description="Delimitación formal del problema de investigación.",
        deadline_days=20,
        formats=("pdf",),
    ),
]


async def seed() -> None:
    """Crea cuentas y proyectos de demostración de forma idempotente."""
    created_users = 0
    skipped_users = 0
    created_projects = 0
    skipped_projects = 0
    created_deliverables = 0
    skipped_deliverables = 0

    async with SessionLocal() as db:
        for name, email, user_type in DEMO_USERS:
            normalized_email = email.lower()
            existing = await db.scalar(
                select(Usuario).where(Usuario.correo == normalized_email)
            )
            if existing is not None:
                skipped_users += 1
                continue

            db.add(
                Usuario(
                    nombre=name,
                    correo=normalized_email,
                    tipo=user_type,
                    credencial=hash_password(DEMO_PASSWORD),
                    estado=UserStatus.ACTIVE,
                )
            )
            created_users += 1

        await db.flush()

        demo_emails = {email.lower() for _, email, _ in DEMO_USERS}
        users = (
            await db.scalars(select(Usuario).where(Usuario.correo.in_(demo_emails)))
        ).all()
        users_by_email = {user.correo: user for user in users}

        for demo_project in DEMO_PROJECTS:
            existing_project = await db.scalar(
                select(Proyecto).where(Proyecto.tema == demo_project.topic)
            )
            if existing_project is not None:
                skipped_projects += 1
                continue

            project = Proyecto(
                tipo=demo_project.project_type,
                tema=demo_project.topic,
                estado=ProjectStatus.ACTIVE,
            )
            db.add(project)
            await db.flush()

            for email in demo_project.managers:
                user = users_by_email[email.lower()]
                db.add(
                    Participacion(
                        usuario_id=user.id,
                        proyecto_id=project.id,
                        rol=ParticipantRole.MANAGER,
                    )
                )

            for email in demo_project.collaborators:
                user = users_by_email[email.lower()]
                db.add(
                    Participacion(
                        usuario_id=user.id,
                        proyecto_id=project.id,
                        rol=ParticipantRole.COLLABORATOR,
                    )
                )

            for order, milestone_name in enumerate(demo_project.milestones, start=1):
                db.add(
                    Hito(
                        proyecto_id=project.id,
                        nombre=milestone_name,
                        orden=order,
                        estado=MilestoneStatus.PENDING,
                    )
                )

            created_projects += 1

        await db.flush()
        now = datetime.now(UTC)

        for demo_deliverable in DEMO_DELIVERABLES:
            project = await db.scalar(
                select(Proyecto).where(Proyecto.tema == demo_deliverable.project_topic)
            )
            if project is None:
                skipped_deliverables += 1
                continue

            milestone = await db.scalar(
                select(Hito).where(
                    Hito.proyecto_id == project.id,
                    Hito.nombre == demo_deliverable.milestone_name,
                )
            )
            if milestone is None:
                skipped_deliverables += 1
                continue

            existing_deliverable = await db.scalar(
                select(Entregable).where(
                    Entregable.hito_id == milestone.id,
                    Entregable.titulo == demo_deliverable.title,
                )
            )
            if existing_deliverable is not None:
                skipped_deliverables += 1
                continue

            db.add(
                Entregable(
                    hito_id=milestone.id,
                    titulo=demo_deliverable.title,
                    descripcion=demo_deliverable.description,
                    fecha_limite=now + timedelta(days=demo_deliverable.deadline_days),
                    formatos_admitidos=list(demo_deliverable.formats),
                    tamano_max_mb=50,
                    estado=DeliverableStatus.PENDING,
                )
            )
            project.fecha_ultima_modificacion = now
            project.modified_at = now
            created_deliverables += 1

        await db.commit()

    print(
        "Seed completado: "
        f"{created_users} cuentas creadas, {skipped_users} existentes; "
        f"{created_projects} proyectos creados, {skipped_projects} existentes; "
        f"{created_deliverables} entregables creados, "
        f"{skipped_deliverables} existentes."
    )
    print(f"Contraseña de demostración: {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
