import asyncio
import hashlib
import re
import unicodedata
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Usuario
from app.modules.auth.security import hash_password
from app.modules.deliverables.enums import (
    DeliverableStatus,
    ForumMessageType,
    ReviewDecision,
)
from app.modules.deliverables.models import (
    Comentario,
    Entrega,
    Entregable,
    Revision,
)
from app.modules.projects.enums import (
    MilestoneStatus,
    ParticipantRole,
    ProjectStatus,
    ProjectType,
)
from app.modules.projects.models import Hito, Participacion, Proyecto
from app.modules.storage.models import Archivo
from app.modules.storage.service import StorageBackend, get_storage

DEMO_PASSWORD = "1234"

CAMILA = "camila.soto@udec.cl"
RODRIGO = "rodrigo.pena@udec.cl"
ANTONIO = "antonio.skorin@udec.cl"
PAULA = "paula.herrera@udec.cl"
CRISTIAN = "cristian.munoz@udec.cl"

JAVIERA = "javiera.contreras@udec.cl"
BENJAMIN = "benjamin.aravena@udec.cl"
MATIAS = "matias.riquelme@udec.cl"
FERNANDA = "fernanda.torres@udec.cl"
VALENTINA = "valentina.rojas@udec.cl"
IGNACIO = "ignacio.fuentes@udec.cl"
MARTINA = "martina.lagos@udec.cl"
TOMAS = "tomas.sepulveda@udec.cl"
ISIDORA = "isidora.paredes@udec.cl"
DIEGO = "diego.salazar@udec.cl"
SEBASTIAN = "sebastian.vera@udec.cl"

DEMO_USERS: list[tuple[str, str, UserType]] = [
    ("Camila Soto", CAMILA, UserType.PROFESSOR),
    ("Rodrigo Peña", RODRIGO, UserType.PROFESSOR),
    ("Antonio Skorin", ANTONIO, UserType.PROFESSOR),
    ("Paula Herrera", PAULA, UserType.PROFESSOR),
    ("Cristián Muñoz", CRISTIAN, UserType.PROFESSOR),
    ("Javiera Contreras", JAVIERA, UserType.STUDENT),
    ("Benjamín Aravena", BENJAMIN, UserType.STUDENT),
    ("Matías Riquelme", MATIAS, UserType.STUDENT),
    ("Fernanda Torres", FERNANDA, UserType.STUDENT),
    ("Valentina Rojas", VALENTINA, UserType.STUDENT),
    ("Ignacio Fuentes", IGNACIO, UserType.STUDENT),
    ("Martina Lagos", MARTINA, UserType.STUDENT),
    ("Tomás Sepúlveda", TOMAS, UserType.STUDENT),
    ("Isidora Paredes", ISIDORA, UserType.STUDENT),
    ("Diego Salazar", DIEGO, UserType.STUDENT),
    ("Sebastián Vera", SEBASTIAN, UserType.STUDENT),
]

TOPIC_GESTURES = (
    "Reconocimiento de gestos para interfaces sin contacto en laboratorios clínicos"
)
TOPIC_HERITAGE = "Reconstrucción 3D de sitios patrimoniales con fotogrametría"
TOPIC_WRITING = "Modelos de lenguaje para retroalimentación automática de escritura"
TOPIC_CONSENSUS = "Verificación formal de protocolos de consenso"

PROJECT_MILESTONES: dict[ProjectType, tuple[str, ...]] = {
    ProjectType.MEMOIR: (
        "Propuesta de memoria",
        "Desarrollo y validación",
        "Informe final y defensa",
        "Cierre y difusión",
    ),
    ProjectType.THESIS: (
        "Propuesta de tesis",
        "Avances y escritura",
        "Escritura final",
        "Defensa",
    ),
    ProjectType.RESEARCH: (
        "Definición del problema",
        "Revisión y diseño",
        "Desarrollo y validación",
        "Publicación y cierre",
    ),
}


@dataclass(frozen=True)
class DemoProject:
    """Datos de un proyecto de demostración."""

    topic: str
    project_type: ProjectType
    managers: tuple[str, ...]
    collaborators: tuple[str, ...]
    status: ProjectStatus = ProjectStatus.ACTIVE
    started_days_ago: int = 120
    closed_days_ago: int | None = None


@dataclass(frozen=True)
class DemoDeliverableTemplate:
    """Plantilla de entregable para una etapa del proyecto."""

    title: str
    description: str
    formats: tuple[str, ...]


@dataclass(frozen=True)
class DemoDeliverable:
    """Entregable heredado de la versión anterior del seed."""

    project_topic: str
    milestone_name: str
    title: str
    description: str
    formats: tuple[str, ...]
    status: DeliverableStatus


DEMO_PROJECTS: list[DemoProject] = [
    DemoProject(
        topic=TOPIC_GESTURES,
        project_type=ProjectType.MEMOIR,
        managers=(CAMILA, RODRIGO),
        collaborators=(JAVIERA,),
        started_days_ago=170,
    ),
    DemoProject(
        topic=TOPIC_HERITAGE,
        project_type=ProjectType.MEMOIR,
        managers=(CAMILA,),
        collaborators=(BENJAMIN,),
        status=ProjectStatus.CLOSED,
        started_days_ago=260,
        closed_days_ago=25,
    ),
    DemoProject(
        topic=TOPIC_WRITING,
        project_type=ProjectType.THESIS,
        managers=(CAMILA,),
        collaborators=(MATIAS,),
        started_days_ago=150,
    ),
    DemoProject(
        topic=TOPIC_CONSENSUS,
        project_type=ProjectType.THESIS,
        managers=(ANTONIO,),
        collaborators=(FERNANDA,),
        status=ProjectStatus.CLOSED,
        started_days_ago=240,
        closed_days_ago=15,
    ),
    DemoProject(
        topic="Asistente de navegación indoor para personas con discapacidad visual",
        project_type=ProjectType.MEMOIR,
        managers=(CAMILA, PAULA),
        collaborators=(VALENTINA, IGNACIO),
        started_days_ago=110,
    ),
    DemoProject(
        topic="Análisis de accesibilidad en plataformas universitarias",
        project_type=ProjectType.MEMOIR,
        managers=(RODRIGO,),
        collaborators=(MARTINA, TOMAS),
        started_days_ago=95,
    ),
    DemoProject(
        topic="Sistema de recomendación de trayectorias académicas",
        project_type=ProjectType.MEMOIR,
        managers=(PAULA,),
        collaborators=(ISIDORA, DIEGO),
        started_days_ago=80,
    ),
    DemoProject(
        topic="Visualización interactiva de datos sísmicos",
        project_type=ProjectType.MEMOIR,
        managers=(ANTONIO,),
        collaborators=(VALENTINA, SEBASTIAN),
        status=ProjectStatus.CLOSED,
        started_days_ago=220,
        closed_days_ago=20,
    ),
    DemoProject(
        topic="Plataforma de apoyo a la escritura de tesis",
        project_type=ProjectType.MEMOIR,
        managers=(CRISTIAN,),
        collaborators=(FERNANDA, IGNACIO),
        started_days_ago=130,
    ),
    DemoProject(
        topic="Aprendizaje federado para datos clínicos",
        project_type=ProjectType.THESIS,
        managers=(CAMILA, ANTONIO),
        collaborators=(JAVIERA, MATIAS),
        started_days_ago=140,
    ),
    DemoProject(
        topic="Optimización de rutas para logística urbana",
        project_type=ProjectType.THESIS,
        managers=(RODRIGO,),
        collaborators=(BENJAMIN, MARTINA),
        started_days_ago=115,
    ),
    DemoProject(
        topic="Detección de anomalías en redes industriales",
        project_type=ProjectType.THESIS,
        managers=(PAULA,),
        collaborators=(TOMAS, ISIDORA),
        started_days_ago=100,
    ),
    DemoProject(
        topic="Modelos multimodales para diagnóstico asistido",
        project_type=ProjectType.THESIS,
        managers=(CAMILA,),
        collaborators=(VALENTINA, DIEGO),
        started_days_ago=85,
    ),
    DemoProject(
        topic="Compresión de modelos para dispositivos de borde",
        project_type=ProjectType.THESIS,
        managers=(CRISTIAN,),
        collaborators=(SEBASTIAN, FERNANDA),
        status=ProjectStatus.CLOSED,
        started_days_ago=210,
        closed_days_ago=30,
    ),
    DemoProject(
        topic="Análisis de sentimiento en redes sociales para salud pública",
        project_type=ProjectType.RESEARCH,
        managers=(CAMILA,),
        collaborators=(JAVIERA, IGNACIO),
        started_days_ago=125,
    ),
    DemoProject(
        topic="Visión computacional para monitoreo de cultivos",
        project_type=ProjectType.RESEARCH,
        managers=(RODRIGO,),
        collaborators=(BENJAMIN, MARTINA),
        started_days_ago=105,
    ),
    DemoProject(
        topic="Gemelos digitales para mantenimiento predictivo",
        project_type=ProjectType.RESEARCH,
        managers=(ANTONIO,),
        collaborators=(MATIAS, TOMAS),
        started_days_ago=90,
    ),
    DemoProject(
        topic="Verificación de contratos inteligentes",
        project_type=ProjectType.RESEARCH,
        managers=(PAULA,),
        collaborators=(ISIDORA, SEBASTIAN),
        status=ProjectStatus.CLOSED,
        started_days_ago=200,
        closed_days_ago=10,
    ),
    DemoProject(
        topic="Interfaces cerebro-computador para rehabilitación",
        project_type=ProjectType.RESEARCH,
        managers=(CAMILA, CRISTIAN),
        collaborators=(VALENTINA, DIEGO),
        started_days_ago=75,
    ),
    DemoProject(
        topic="Privacidad diferencial en datos educativos",
        project_type=ProjectType.RESEARCH,
        managers=(RODRIGO,),
        collaborators=(FERNANDA, IGNACIO),
        started_days_ago=60,
    ),
]

DELIVERABLE_TEMPLATES: tuple[tuple[DemoDeliverableTemplate, ...], ...] = (
    (
        DemoDeliverableTemplate(
            "Documento de propuesta",
            "Documento inicial con el alcance y los objetivos del proyecto.",
            ("pdf",),
        ),
        DemoDeliverableTemplate(
            "Presentación de propuesta",
            "Presentación para exponer la propuesta al equipo gestor.",
            ("pdf",),
        ),
        DemoDeliverableTemplate(
            "Plan de trabajo",
            "Carta Gantt y planificación de las siguientes etapas.",
            ("pdf", "zip"),
        ),
    ),
    (
        DemoDeliverableTemplate(
            "Informe de avance",
            "Informe con los avances técnicos y resultados preliminares.",
            ("pdf",),
        ),
        DemoDeliverableTemplate(
            "Demostración funcional",
            "Evidencia de funcionamiento del prototipo o componente desarrollado.",
            ("pdf", "zip"),
        ),
        DemoDeliverableTemplate(
            "Documentación técnica",
            "Documentación de arquitectura, decisiones y pruebas realizadas.",
            ("pdf", "zip"),
        ),
    ),
    (
        DemoDeliverableTemplate(
            "Informe de validación",
            "Resultados de validación, métricas y análisis de errores.",
            ("pdf",),
        ),
        DemoDeliverableTemplate(
            "Artículo o capítulo",
            "Borrador del artículo o capítulo derivado del trabajo.",
            ("pdf",),
        ),
        DemoDeliverableTemplate(
            "Anexos",
            "Anexos, datasets y material complementario del proyecto.",
            ("pdf", "zip"),
        ),
    ),
    (
        DemoDeliverableTemplate(
            "Informe final",
            "Versión final del documento para revisión y defensa.",
            ("pdf",),
        ),
        DemoDeliverableTemplate(
            "Presentación de defensa",
            "Presentación utilizada en la defensa del proyecto.",
            ("pdf",),
        ),
        DemoDeliverableTemplate(
            "Repositorio de código",
            "Enlace o archivo con el código y las instrucciones de ejecución.",
            ("pdf", "zip"),
        ),
    ),
)

LEGACY_DELIVERABLES: tuple[DemoDeliverable, ...] = (
    DemoDeliverable(
        project_topic=TOPIC_GESTURES,
        milestone_name="Propuesta de memoria",
        title="Anteproyecto",
        description="Propuesta inicial de la memoria de título.",
        formats=("pdf",),
        status=DeliverableStatus.APPROVED,
    ),
    DemoDeliverable(
        project_topic=TOPIC_GESTURES,
        milestone_name="Desarrollo y validación",
        title="Informe de avance 1",
        description="Primer informe de avance del trabajo experimental.",
        formats=("pdf", "zip"),
        status=DeliverableStatus.APPROVED,
    ),
    DemoDeliverable(
        project_topic=TOPIC_GESTURES,
        milestone_name="Desarrollo y validación",
        title="Prototipo funcional",
        description="Prototipo y evidencia de funcionamiento.",
        formats=("pdf", "zip"),
        status=DeliverableStatus.CHANGES_REQUESTED,
    ),
    DemoDeliverable(
        project_topic=TOPIC_GESTURES,
        milestone_name="Informe final y defensa",
        title="Informe final",
        description="Versión final de la memoria para revisión y defensa.",
        formats=("pdf",),
        status=DeliverableStatus.SUBMITTED,
    ),
    DemoDeliverable(
        project_topic=TOPIC_WRITING,
        milestone_name="Propuesta de tesis",
        title="Propuesta de tesis",
        description="Documento de propuesta de la tesis de magíster.",
        formats=("pdf",),
        status=DeliverableStatus.APPROVED,
    ),
    DemoDeliverable(
        project_topic=TOPIC_WRITING,
        milestone_name="Avances y escritura",
        title="Avance 1",
        description="Primer avance del trabajo de tesis.",
        formats=("pdf", "zip"),
        status=DeliverableStatus.CHANGES_REQUESTED,
    ),
    DemoDeliverable(
        project_topic=TOPIC_CONSENSUS,
        milestone_name="Propuesta de tesis",
        title="Definición del problema",
        description="Delimitación formal del problema de investigación.",
        formats=("pdf",),
        status=DeliverableStatus.APPROVED,
    ),
)

DELIVERABLE_STATUS_PATTERN: tuple[DeliverableStatus, ...] = (
    DeliverableStatus.APPROVED,
    DeliverableStatus.APPROVED,
    DeliverableStatus.SUBMITTED,
    DeliverableStatus.CHANGES_REQUESTED,
    DeliverableStatus.PENDING,
    DeliverableStatus.APPROVED,
    DeliverableStatus.SUBMITTED,
    DeliverableStatus.PENDING,
    DeliverableStatus.CHANGES_REQUESTED,
    DeliverableStatus.APPROVED,
    DeliverableStatus.APPROVED,
    DeliverableStatus.SUBMITTED,
)

DEMO_MESSAGES: tuple[str, ...] = (
    "¿Alguna duda con el formato del documento?",
    "Subí una nueva versión con los ajustes solicitados.",
    "Revisemos los plazos en la próxima reunión.",
    "Quedo atento a la retroalimentación.",
    "El enlace incluye los anexos actualizados.",
    "¿Podemos coordinar una reunión para revisar el avance?",
    "Gracias por la revisión; incorporé los comentarios.",
    "El prototipo ya está disponible en el repositorio.",
    "Documenté las decisiones en el informe.",
    "¿El formato del entregable es el correcto?",
    "Adjunté una versión corregida para revisión.",
    "Avísame si necesitas algún antecedente adicional.",
)


def _build_demo_pdf() -> bytes:
    """Genera un PDF mínimo y válido para los adjuntos sintéticos."""
    content = (
        b"BT /F1 18 Tf 72 720 Td (Hito - documento sintetico de demostracion) Tj ET"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    output = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


DEMO_PDF_BYTES = _build_demo_pdf()
DEMO_PDF_SHA256 = hashlib.sha256(DEMO_PDF_BYTES).hexdigest()
DEMO_PDF_SIZE = len(DEMO_PDF_BYTES)


@dataclass(frozen=True)
class DeliverableSeed:
    """Entregable listo para sembrar su ciclo de vida."""

    project: Proyecto
    deliverable: Entregable
    project_index: int
    position: int
    status: DeliverableStatus


@dataclass(frozen=True)
class LifecycleResult:
    """Resumen de las filas creadas para un entregable."""

    latest_activity: datetime
    submissions: int
    reviews: int
    messages: int
    files: int


def _slug(value: str) -> str:
    """Convierte un título en un nombre de archivo ASCII."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug[:80].rstrip("-") or "entregable"


async def _single_chunk(data: bytes) -> AsyncIterator[bytes]:
    yield data


def _status_for(project: Proyecto, position: int) -> DeliverableStatus:
    if project.estado == ProjectStatus.CLOSED:
        return DeliverableStatus.APPROVED
    return DELIVERABLE_STATUS_PATTERN[position % len(DELIVERABLE_STATUS_PATTERN)]


def _deadline_for(
    project_index: int,
    status: DeliverableStatus,
    position: int,
    now: datetime,
) -> datetime:
    if status == DeliverableStatus.APPROVED:
        return now - timedelta(days=10 + position + project_index % 7)
    if status == DeliverableStatus.SUBMITTED:
        return now + timedelta(days=5 + position + project_index % 5)
    if status == DeliverableStatus.CHANGES_REQUESTED:
        if position == 8:
            return now - timedelta(days=3 + project_index % 4)
        return now + timedelta(days=7 + position + project_index % 5)
    if position == 4:
        return now - timedelta(days=4 + project_index % 5)
    return now + timedelta(days=10 + position + project_index % 5)


def _versions_for(
    project_index: int,
    status: DeliverableStatus,
    position: int,
    deadline: datetime,
    now: datetime,
) -> list[tuple[datetime, ReviewDecision | None]]:
    if status == DeliverableStatus.PENDING:
        return []

    if status == DeliverableStatus.APPROVED:
        if (project_index + position) % 3 == 0:
            submitted = min(deadline - timedelta(days=2), now - timedelta(days=3))
            return [(submitted, ReviewDecision.APPROVED)]
        latest = min(deadline - timedelta(days=2), now - timedelta(days=2))
        first = latest - timedelta(days=8)
        return [
            (first, ReviewDecision.CHANGES_REQUESTED),
            (latest, ReviewDecision.APPROVED),
        ]

    if status == DeliverableStatus.SUBMITTED:
        first = min(deadline - timedelta(days=4), now - timedelta(days=5))
        if (project_index + position) % 4 != 0:
            return [(first, None)]
        latest = min(deadline - timedelta(days=1), now - timedelta(days=1))
        if latest <= first:
            first = latest - timedelta(days=3)
        return [
            (first, ReviewDecision.CHANGES_REQUESTED),
            (latest, None),
        ]

    first = min(deadline - timedelta(days=3), now - timedelta(days=2))
    if (project_index + position) % 2 != 0:
        return [(first, ReviewDecision.CHANGES_REQUESTED)]
    latest = min(deadline - timedelta(days=1), now - timedelta(days=1))
    if latest <= first:
        first = latest - timedelta(days=3)
    return [
        (first, ReviewDecision.CHANGES_REQUESTED),
        (latest, ReviewDecision.CHANGES_REQUESTED),
    ]


def _review_time(submitted_at: datetime, now: datetime) -> datetime:
    return min(submitted_at + timedelta(days=1), now - timedelta(hours=2))


def _submission_has_file(project_index: int, position: int, version: int) -> bool:
    return (project_index + position + version) % 3 == 0


def _submission_link(
    project_index: int,
    position: int,
    version: int,
) -> str | None:
    token = project_index + position + version
    if token % 3 == 0 and token % 2 == 0:
        return None
    return (
        f"https://example.com/hito/{project_index + 1}/"
        f"entregables/{position + 1}/v{version}"
    )


def _review_has_file(project_index: int, position: int, version: int) -> bool:
    return (project_index + position + version) % 4 == 0


def _append_comment(
    db: AsyncSession,
    deliverable_id: uuid.UUID,
    text: str,
    when: datetime,
    author_id: uuid.UUID | None = None,
) -> None:
    db.add(
        Comentario(
            entregable_id=deliverable_id,
            autor_id=author_id,
            tipo=(
                ForumMessageType.USER
                if author_id is not None
                else ForumMessageType.SYSTEM
            ),
            texto=text,
            fecha=when,
        )
    )


async def _save_demo_file(
    storage: StorageBackend,
    key: str,
    filename: str,
    *,
    entrega_id: uuid.UUID | None = None,
    revision_id: uuid.UUID | None = None,
) -> Archivo:
    await storage.save(key, _single_chunk(DEMO_PDF_BYTES))
    return Archivo(
        entrega_id=entrega_id,
        revision_id=revision_id,
        nombre=filename,
        tipo_mime="application/pdf",
        tamano=DEMO_PDF_SIZE,
        clave_almacenamiento=key,
        sha256=DEMO_PDF_SHA256,
    )


async def _seed_lifecycle(
    db: AsyncSession,
    storage: StorageBackend,
    seed: DeliverableSeed,
    managers: list[Usuario],
    collaborators: list[Usuario],
    now: datetime,
    saved_keys: list[str],
) -> LifecycleResult:
    deliverable = seed.deliverable
    project = seed.project
    deadline = deliverable.fecha_limite
    created_at = now - timedelta(days=70 + seed.project_index % 10)
    latest_activity = created_at
    created_submissions = 0
    created_reviews = 0
    created_messages = 1
    created_files = 0

    _append_comment(
        db,
        deliverable.id,
        f"{managers[0].nombre} ha creado el entregable.",
        created_at,
    )

    versions = _versions_for(
        seed.project_index,
        seed.status,
        seed.position,
        deadline,
        now,
    )

    for version, (submitted_at, review_decision) in enumerate(versions, start=1):
        submission_id = uuid.uuid4()
        author = collaborators[
            (seed.position + seed.project_index + version) % len(collaborators)
        ]
        link_url = _submission_link(seed.project_index, seed.position, version)
        db.add(
            Entrega(
                id=submission_id,
                entregable_id=deliverable.id,
                version=version,
                autor_id=author.id,
                fecha_envio=submitted_at,
                enlace=link_url,
            )
        )
        _append_comment(
            db,
            deliverable.id,
            f"{author.nombre} ha entregado la versión {version}.",
            submitted_at,
        )
        created_submissions += 1
        created_messages += 1
        latest_activity = max(latest_activity, submitted_at)

        if _submission_has_file(seed.project_index, seed.position, version):
            key = (
                f"projects/{project.id}/deliverables/{deliverable.id}/"
                f"submissions/{submission_id}/{uuid.uuid4().hex}"
            )
            saved_keys.append(key)
            db.add(
                await _save_demo_file(
                    storage,
                    key,
                    f"{_slug(deliverable.titulo)}-v{version}.pdf",
                    entrega_id=submission_id,
                )
            )
            created_files += 1

        if review_decision is None:
            continue

        review_id = uuid.uuid4()
        review_at = _review_time(submitted_at, now)
        reviewer = managers[
            (seed.position + seed.project_index + version) % len(managers)
        ]
        db.add(
            Revision(
                id=review_id,
                entrega_id=submission_id,
                gestor_id=reviewer.id,
                decision=review_decision,
                fecha=review_at,
            )
        )
        created_reviews += 1
        latest_activity = max(latest_activity, review_at)

        if review_decision == ReviewDecision.APPROVED:
            event_text = (
                f"{reviewer.nombre} ha marcado la versión {version} como Aprobada"
            )
        else:
            event_text = (
                f"{reviewer.nombre} ha solicitado cambios en la versión {version}"
            )

        if _review_has_file(seed.project_index, seed.position, version):
            key = (
                f"projects/{project.id}/deliverables/{deliverable.id}/"
                f"reviews/{review_id}/{uuid.uuid4().hex}"
            )
            saved_keys.append(key)
            db.add(
                await _save_demo_file(
                    storage,
                    key,
                    f"revision-{_slug(deliverable.titulo)}-v{version}.pdf",
                    revision_id=review_id,
                )
            )
            created_files += 1
            event_text += " y adjuntó 1 archivo"

        _append_comment(
            db,
            deliverable.id,
            event_text + ".",
            review_at,
        )
        created_messages += 1

    message_count = 2 + (seed.project_index + seed.position) % 3
    for index in range(message_count):
        if index % 2 == 0:
            author = collaborators[(seed.position + index) % len(collaborators)]
        else:
            author = managers[(seed.project_index + index) % len(managers)]
        text = DEMO_MESSAGES[
            (seed.project_index * 3 + seed.position + index) % len(DEMO_MESSAGES)
        ]
        when = now - timedelta(
            days=1 + (seed.project_index + seed.position + index) % 45
        )
        _append_comment(db, deliverable.id, text, when, author.id)
        created_messages += 1
        latest_activity = max(latest_activity, when)

    return LifecycleResult(
        latest_activity=latest_activity,
        submissions=created_submissions,
        reviews=created_reviews,
        messages=created_messages,
        files=created_files,
    )


def _milestone_state(
    project: Proyecto,
    order: int,
    now: datetime,
) -> tuple[MilestoneStatus, datetime | None]:
    if project.estado == ProjectStatus.CLOSED:
        return (
            MilestoneStatus.COMPLETED,
            now - timedelta(days=40 - order * 8),
        )
    if order <= 2:
        return (
            MilestoneStatus.COMPLETED,
            now - timedelta(days=30 - order * 5),
        )
    if order == 3:
        return MilestoneStatus.IN_PROGRESS, None
    return MilestoneStatus.PENDING, None


async def seed() -> None:
    """Crea cuentas, proyectos y actividad de demostración de forma idempotente."""
    created_users = 0
    skipped_users = 0
    created_projects = 0
    skipped_projects = 0
    created_milestones = 0
    skipped_milestones = 0
    created_deliverables = 0
    skipped_deliverables = 0
    created_submissions = 0
    created_reviews = 0
    created_messages = 0
    created_files = 0
    skipped_lifecycles = 0

    now = datetime.now(UTC)
    storage = get_storage()
    saved_keys: list[str] = []

    try:
        async with SessionLocal() as db:
            demo_emails = {email.lower() for _, email, _ in DEMO_USERS}
            existing_users = (
                await db.scalars(select(Usuario).where(Usuario.correo.in_(demo_emails)))
            ).all()
            users_by_email = {user.correo: user for user in existing_users}

            for name, email, user_type in DEMO_USERS:
                normalized_email = email.lower()
                if normalized_email in users_by_email:
                    skipped_users += 1
                    continue

                user = Usuario(
                    nombre=name,
                    correo=normalized_email,
                    tipo=user_type,
                    credencial=hash_password(DEMO_PASSWORD),
                    estado=UserStatus.ACTIVE,
                    consentimiento_fecha=now,
                    consentimiento_version="demo",
                )
                db.add(user)
                users_by_email[normalized_email] = user
                created_users += 1

            await db.flush()

            demo_topics = [project.topic for project in DEMO_PROJECTS]
            existing_projects = (
                await db.scalars(select(Proyecto).where(Proyecto.tema.in_(demo_topics)))
            ).all()
            projects_by_topic = {project.tema: project for project in existing_projects}
            participants_by_project: dict[int, tuple[list[Usuario], list[Usuario]]] = {}

            for project_index, demo_project in enumerate(DEMO_PROJECTS):
                project = projects_by_topic.get(demo_project.topic)
                started_on = date.today() - timedelta(
                    days=demo_project.started_days_ago
                )
                closed_on = (
                    date.today() - timedelta(days=demo_project.closed_days_ago)
                    if demo_project.closed_days_ago is not None
                    else None
                )

                if project is None:
                    project = Proyecto(
                        tipo=demo_project.project_type,
                        tema=demo_project.topic,
                        estado=demo_project.status,
                        fecha_inicio=started_on,
                        fecha_cierre=closed_on,
                        fecha_ultima_modificacion=(
                            now - timedelta(hours=project_index + 1)
                        ),
                    )
                    db.add(project)
                    projects_by_topic[demo_project.topic] = project
                    created_projects += 1
                else:
                    project.tipo = demo_project.project_type
                    project.estado = demo_project.status
                    project.fecha_inicio = started_on
                    project.fecha_cierre = closed_on
                    skipped_projects += 1

                managers = [
                    users_by_email[email.lower()] for email in demo_project.managers
                ]
                collaborators = [
                    users_by_email[email.lower()]
                    for email in demo_project.collaborators
                ]
                participants_by_project[project_index] = (
                    managers,
                    collaborators,
                )

                for user in managers:
                    existing_participation = await db.scalar(
                        select(Participacion).where(
                            Participacion.usuario_id == user.id,
                            Participacion.proyecto_id == project.id,
                        )
                    )
                    if existing_participation is None:
                        db.add(
                            Participacion(
                                usuario_id=user.id,
                                proyecto_id=project.id,
                                rol=ParticipantRole.MANAGER,
                            )
                        )

                for user in collaborators:
                    existing_participation = await db.scalar(
                        select(Participacion).where(
                            Participacion.usuario_id == user.id,
                            Participacion.proyecto_id == project.id,
                        )
                    )
                    if existing_participation is None:
                        db.add(
                            Participacion(
                                usuario_id=user.id,
                                proyecto_id=project.id,
                                rol=ParticipantRole.COLLABORATOR,
                            )
                        )

            await db.flush()

            deliverable_seeds: list[DeliverableSeed] = []

            for project_index, demo_project in enumerate(DEMO_PROJECTS):
                project = projects_by_topic[demo_project.topic]
                milestone_names = PROJECT_MILESTONES[demo_project.project_type]
                existing_milestones = (
                    await db.scalars(select(Hito).where(Hito.proyecto_id == project.id))
                ).all()
                milestones_by_order = {
                    milestone.orden: milestone for milestone in existing_milestones
                }

                for order, milestone_name in enumerate(milestone_names, start=1):
                    state, completed_at = _milestone_state(project, order, now)
                    milestone = milestones_by_order.get(order)
                    if milestone is None:
                        milestone = Hito(
                            proyecto_id=project.id,
                            nombre=milestone_name,
                            orden=order,
                            estado=state,
                            fecha_completado=completed_at,
                        )
                        db.add(milestone)
                        milestones_by_order[order] = milestone
                        created_milestones += 1
                    else:
                        milestone.nombre = milestone_name
                        milestone.estado = state
                        milestone.fecha_completado = completed_at
                        skipped_milestones += 1

                await db.flush()

                milestone_ids = [milestones_by_order[order].id for order in range(1, 5)]
                existing_deliverables = (
                    await db.scalars(
                        select(Entregable).where(Entregable.hito_id.in_(milestone_ids))
                    )
                ).all()
                deliverables_by_key = {
                    (deliverable.hito_id, deliverable.titulo): deliverable
                    for deliverable in existing_deliverables
                }

                for order, milestone_name in enumerate(milestone_names, start=1):
                    milestone = milestones_by_order[order]
                    legacy_by_title = {
                        legacy.title: legacy
                        for legacy in LEGACY_DELIVERABLES
                        if legacy.project_topic == demo_project.topic
                        and legacy.milestone_name == milestone_name
                    }
                    templates = list(DELIVERABLE_TEMPLATES[order - 1])
                    for legacy in legacy_by_title.values():
                        if not any(
                            template.title == legacy.title for template in templates
                        ):
                            templates.append(
                                DemoDeliverableTemplate(
                                    legacy.title,
                                    legacy.description,
                                    legacy.formats,
                                )
                            )

                    for template_index, template in enumerate(templates):
                        position = (order - 1) * 3 + template_index
                        legacy = legacy_by_title.get(template.title)
                        if legacy is not None:
                            status = legacy.status
                        else:
                            status = _status_for(project, position)
                        if project.estado == ProjectStatus.CLOSED:
                            status = DeliverableStatus.APPROVED
                        deadline = _deadline_for(project_index, status, position, now)
                        key = (milestone.id, template.title)
                        deliverable = deliverables_by_key.get(key)

                        if deliverable is None:
                            deliverable = Entregable(
                                hito_id=milestone.id,
                                titulo=template.title,
                                descripcion=template.description,
                                fecha_limite=deadline,
                                formatos_admitidos=list(template.formats),
                                tamano_max_mb=50,
                                estado=status,
                                created_at=(
                                    now - timedelta(days=70 + project_index % 10)
                                ),
                                modified_at=now,
                            )
                            db.add(deliverable)
                            deliverables_by_key[key] = deliverable
                            created_deliverables += 1
                        else:
                            existing_submission = await db.scalar(
                                select(Entrega.id)
                                .where(Entrega.entregable_id == deliverable.id)
                                .limit(1)
                            )
                            if existing_submission is None:
                                deliverable.descripcion = template.description
                                deliverable.fecha_limite = deadline
                                deliverable.formatos_admitidos = list(template.formats)
                                deliverable.tamano_max_mb = 50
                                deliverable.estado = status
                            skipped_deliverables += 1

                        deliverable_seeds.append(
                            DeliverableSeed(
                                project=project,
                                deliverable=deliverable,
                                project_index=project_index,
                                position=position,
                                status=status,
                            )
                        )

                await db.flush()

            deliverable_ids = [seed.deliverable.id for seed in deliverable_seeds]
            submitted_ids = set(
                (
                    await db.scalars(
                        select(Entrega.entregable_id)
                        .where(Entrega.entregable_id.in_(deliverable_ids))
                        .distinct()
                    )
                ).all()
            )
            commented_ids = set(
                (
                    await db.scalars(
                        select(Comentario.entregable_id)
                        .where(Comentario.entregable_id.in_(deliverable_ids))
                        .distinct()
                    )
                ).all()
            )
            project_latest: dict[uuid.UUID, datetime] = {}

            for seed_spec in deliverable_seeds:
                if (
                    seed_spec.deliverable.id in submitted_ids
                    or seed_spec.deliverable.id in commented_ids
                ):
                    skipped_lifecycles += 1
                    continue

                managers, collaborators = participants_by_project[
                    seed_spec.project_index
                ]
                result = await _seed_lifecycle(
                    db,
                    storage,
                    seed_spec,
                    managers,
                    collaborators,
                    now,
                    saved_keys,
                )
                created_submissions += result.submissions
                created_reviews += result.reviews
                created_messages += result.messages
                created_files += result.files
                previous_activity = project_latest.get(seed_spec.project.id)
                if (
                    previous_activity is None
                    or result.latest_activity > previous_activity
                ):
                    project_latest[seed_spec.project.id] = result.latest_activity

            for project in projects_by_topic.values():
                if project.id not in project_latest:
                    continue
                latest_activity = project_latest[project.id]
                project.fecha_ultima_modificacion = latest_activity
                project.modified_at = latest_activity

            await db.commit()
    except Exception:
        for key in saved_keys:
            await storage.delete(key)
        raise

    print(
        "Seed completado: "
        f"{created_users} cuentas creadas, {skipped_users} existentes; "
        f"{created_projects} proyectos creados, {skipped_projects} existentes; "
        f"{created_milestones} hitos creados, "
        f"{skipped_milestones} existentes; "
        f"{created_deliverables} entregables creados, "
        f"{skipped_deliverables} existentes; "
        f"{created_submissions} entregas, {created_reviews} revisiones, "
        f"{created_messages} mensajes y {created_files} archivos creados; "
        f"{skipped_lifecycles} ciclos existentes."
    )
    print(f"Contraseña de demostración: {DEMO_PASSWORD}")
    print(f"Cuenta principal: {CAMILA}")


if __name__ == "__main__":
    asyncio.run(seed())
