from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Usuario
from app.modules.deliverables.enums import DeliverableStatus
from app.modules.deliverables.models import Entrega, Entregable, Revision
from app.modules.projects.enums import MilestoneStatus, ParticipantRole, ProjectStatus
from app.modules.projects.models import Hito, Participacion, Proyecto
from app.modules.projects.schemas import (
    DELIVERABLE_STATUS_DB_TO_API,
    PARTICIPANT_ROLE_DB_TO_API,
    PROJECT_STATUS_DB_TO_API,
    PROJECT_TYPE_API_TO_DB,
    PROJECT_TYPE_DB_TO_API,
    REVIEW_DECISION_DB_TO_API,
    DeliverableSummary,
    LatestSubmissionResponse,
    MilestoneCreate,
    MilestoneResponse,
    ParticipantResponse,
    ParticipantRoleApi,
    ProjectCreate,
    ProjectDetail,
    ProjectListItem,
    ProjectUpdate,
    ReviewSummary,
)


@dataclass(frozen=True)
class ProjectCounts:
    """Resumen calculado de entregables de un proyecto."""

    total: int
    approved: int
    overdue: int
    pending_review: int
    next_deadline: datetime | None


def _touch_project(project: Proyecto, now: datetime) -> None:
    project.fecha_ultima_modificacion = now
    project.modified_at = now


async def _resolve_participants(
    db: AsyncSession,
    manager_emails: list[str],
    collaborator_emails: list[str],
    *,
    creator: Usuario | None = None,
) -> list[tuple[Usuario, ParticipantRole]]:
    managers = {email.strip().lower() for email in manager_emails}
    collaborators = {email.strip().lower() for email in collaborator_emails}

    if creator is not None:
        managers.add(creator.correo)

    if not collaborators:
        raise AppError(
            "COLLABORATOR_REQUIRED",
            "El proyecto requiere tener al menos un colaborador.",
            422,
        )
    if not managers:
        raise AppError(
            "MANAGER_REQUIRED",
            "El proyecto requiere tener al menos un gestor.",
            422,
        )

    if managers & collaborators:
        raise AppError(
            "DUPLICATE_ROLE",
            "Un usuario no puede tener dos roles en el mismo proyecto.",
            422,
        )

    emails = managers | collaborators
    users = (
        await db.scalars(
            select(Usuario).where(
                Usuario.correo.in_(emails),
                Usuario.estado == UserStatus.ACTIVE,
            )
        )
    ).all()
    users_by_email = {user.correo: user for user in users}

    for email in sorted(emails):
        if email not in users_by_email:
            raise AppError(
                "PARTICIPANT_NOT_FOUND",
                f"No existe una cuenta activa con ese correo: {email}.",
                422,
            )

    participants = [
        (users_by_email[email], ParticipantRole.MANAGER) for email in sorted(managers)
    ]
    participants.extend(
        (users_by_email[email], ParticipantRole.COLLABORATOR)
        for email in sorted(collaborators)
    )
    return participants


async def _load_participants(
    db: AsyncSession, project_id: UUID
) -> list[ParticipantResponse]:
    participations = (
        await db.scalars(
            select(Participacion).where(Participacion.proyecto_id == project_id)
        )
    ).all()
    if not participations:
        return []

    user_ids = [participation.usuario_id for participation in participations]
    users = (await db.scalars(select(Usuario).where(Usuario.id.in_(user_ids)))).all()
    users_by_id = {user.id: user for user in users}

    result: list[ParticipantResponse] = []
    for participation in participations:
        user = users_by_id.get(participation.usuario_id)
        if user is None:
            continue
        result.append(
            ParticipantResponse(
                id=user.id,
                name=user.nombre,
                email=user.correo,
                role=PARTICIPANT_ROLE_DB_TO_API[participation.rol],
            )
        )

    result.sort(key=lambda participant: participant.name.lower())
    return result


async def _has_on_time_submission(db: AsyncSession, deliverable: Entregable) -> bool:
    submission_id = await db.scalar(
        select(Entrega.id)
        .where(
            Entrega.entregable_id == deliverable.id,
            Entrega.fecha_envio <= deliverable.fecha_limite,
        )
        .limit(1)
    )
    return submission_id is not None


async def _is_overdue(db: AsyncSession, deliverable: Entregable, now: datetime) -> bool:
    if deliverable.estado == DeliverableStatus.APPROVED:
        return False
    if now <= deliverable.fecha_limite:
        return False
    return not await _has_on_time_submission(db, deliverable)


async def _serialize_deliverable(
    db: AsyncSession, deliverable: Entregable, now: datetime
) -> DeliverableSummary:
    latest = await db.scalar(
        select(Entrega)
        .where(Entrega.entregable_id == deliverable.id)
        .order_by(Entrega.version.desc())
        .limit(1)
    )

    latest_response: LatestSubmissionResponse | None = None
    review_response: ReviewSummary | None = None

    if latest is not None:
        author = await db.get(Usuario, latest.autor_id)
        latest_response = LatestSubmissionResponse(
            version=latest.version,
            submitted_at=latest.fecha_envio,
            author_name=author.nombre if author is not None else "Usuario eliminado",
        )

        review = await db.scalar(
            select(Revision).where(Revision.entrega_id == latest.id)
        )
        if review is not None:
            reviewer = await db.get(Usuario, review.gestor_id)
            review_response = ReviewSummary(
                decision=REVIEW_DECISION_DB_TO_API[review.decision],
                reviewer_name=(
                    reviewer.nombre if reviewer is not None else "Usuario eliminado"
                ),
                reviewed_at=review.fecha,
            )

    return DeliverableSummary(
        id=deliverable.id,
        title=deliverable.titulo,
        deadline_at=deliverable.fecha_limite,
        status=DELIVERABLE_STATUS_DB_TO_API[deliverable.estado],
        is_overdue=await _is_overdue(db, deliverable, now),
        latest_submission=latest_response,
        review=review_response,
    )


async def _project_counts(
    db: AsyncSession, project_id: UUID, now: datetime
) -> ProjectCounts:
    deliverables = (
        await db.scalars(
            select(Entregable)
            .join(Hito, Entregable.hito_id == Hito.id)
            .where(Hito.proyecto_id == project_id)
        )
    ).all()

    overdue = 0
    for deliverable in deliverables:
        if await _is_overdue(db, deliverable, now):
            overdue += 1

    non_approved_deadlines = [
        deliverable.fecha_limite
        for deliverable in deliverables
        if deliverable.estado != DeliverableStatus.APPROVED
    ]

    return ProjectCounts(
        total=len(deliverables),
        approved=sum(
            1
            for deliverable in deliverables
            if deliverable.estado == DeliverableStatus.APPROVED
        ),
        overdue=overdue,
        pending_review=sum(
            1
            for deliverable in deliverables
            if deliverable.estado == DeliverableStatus.SUBMITTED
        ),
        next_deadline=min(non_approved_deadlines, default=None),
    )


async def build_project_detail(
    db: AsyncSession,
    project: Proyecto,
    my_role: ParticipantRoleApi | None,
) -> ProjectDetail:
    """Serializa un proyecto, sus participantes, hitos y entregables."""
    participants = await _load_participants(db, project.id)
    milestones = (
        await db.scalars(
            select(Hito).where(Hito.proyecto_id == project.id).order_by(Hito.orden)
        )
    ).all()
    now = datetime.now(UTC)

    milestone_responses: list[MilestoneResponse] = []
    for milestone in milestones:
        deliverables = (
            await db.scalars(
                select(Entregable)
                .where(Entregable.hito_id == milestone.id)
                .order_by(
                    Entregable.fecha_limite,
                    Entregable.created_at,
                    Entregable.id,
                )
            )
        ).all()
        deliverable_responses = [
            await _serialize_deliverable(db, deliverable, now)
            for deliverable in deliverables
        ]
        milestone_responses.append(
            MilestoneResponse(
                id=milestone.id,
                name=milestone.nombre,
                order_index=milestone.orden,
                deliverables=deliverable_responses,
            )
        )

    return ProjectDetail(
        id=project.id,
        topic=project.tema,
        project_type=PROJECT_TYPE_DB_TO_API[project.tipo],
        status=PROJECT_STATUS_DB_TO_API[project.estado],
        started_on=project.fecha_inicio,
        last_modified_at=project.fecha_ultima_modificacion,
        my_role=my_role,
        participants=participants,
        milestones=milestone_responses,
    )


async def list_projects_for_user(
    db: AsyncSession, user: Usuario
) -> list[ProjectListItem]:
    """Lista los proyectos del usuario ordenados por última modificación."""
    projects = (
        await db.scalars(
            select(Proyecto)
            .join(Participacion, Participacion.proyecto_id == Proyecto.id)
            .where(Participacion.usuario_id == user.id)
            .order_by(
                Proyecto.fecha_ultima_modificacion.desc(),
                Proyecto.id,
            )
        )
    ).all()

    now = datetime.now(UTC)
    result: list[ProjectListItem] = []

    for project in projects:
        participation = await db.scalar(
            select(Participacion).where(
                Participacion.proyecto_id == project.id,
                Participacion.usuario_id == user.id,
            )
        )
        if participation is None:
            continue

        participants = await _load_participants(db, project.id)
        counts = await _project_counts(db, project.id, now)

        result.append(
            ProjectListItem(
                id=project.id,
                topic=project.tema,
                project_type=PROJECT_TYPE_DB_TO_API[project.tipo],
                status=PROJECT_STATUS_DB_TO_API[project.estado],
                started_on=project.fecha_inicio,
                last_modified_at=project.fecha_ultima_modificacion,
                my_role=PARTICIPANT_ROLE_DB_TO_API[participation.rol],
                participants=participants,
                total_deliverables=counts.total,
                approved_deliverables=counts.approved,
                overdue_deliverables=counts.overdue,
                pending_review_deliverables=counts.pending_review,
                next_deadline_at=counts.next_deadline,
            )
        )

    return result


async def create_project(
    db: AsyncSession, creator: Usuario, payload: ProjectCreate
) -> Proyecto:
    """Crea un proyecto y deja al profesor creador como gestor."""
    if creator.tipo != UserType.PROFESSOR:
        raise AppError(
            "FORBIDDEN",
            "Solo un profesor puede crear proyectos.",
            403,
        )

    topic = payload.topic.strip()
    if not topic:
        raise AppError(
            "PROJECT_TOPIC_REQUIRED",
            "El tema del proyecto no puede estar vacío.",
            422,
        )

    participants = await _resolve_participants(
        db,
        [str(email) for email in payload.manager_emails],
        [str(email) for email in payload.collaborator_emails],
        creator=creator,
    )

    project = Proyecto(
        tipo=PROJECT_TYPE_API_TO_DB[payload.project_type],
        tema=topic,
        estado=ProjectStatus.ACTIVE,
    )
    db.add(project)
    await db.flush()

    for user, role in participants:
        db.add(
            Participacion(
                usuario_id=user.id,
                proyecto_id=project.id,
                rol=role,
            )
        )

    await db.commit()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession, project: Proyecto, payload: ProjectUpdate
) -> Proyecto:
    """Edita la información básica y los participantes de un proyecto."""
    topic = payload.topic.strip()
    if not topic:
        raise AppError(
            "PROJECT_TOPIC_REQUIRED",
            "El tema del proyecto no puede estar vacío.",
            422,
        )

    participants = await _resolve_participants(
        db,
        [str(email) for email in payload.manager_emails],
        [str(email) for email in payload.collaborator_emails],
    )

    project.tema = topic
    project.tipo = PROJECT_TYPE_API_TO_DB[payload.project_type]
    _touch_project(project, datetime.now(UTC))

    await db.execute(
        delete(Participacion).where(Participacion.proyecto_id == project.id)
    )
    await db.flush()

    for user, role in participants:
        db.add(
            Participacion(
                usuario_id=user.id,
                proyecto_id=project.id,
                rol=role,
            )
        )

    await db.commit()
    return project


async def get_participation_role(
    db: AsyncSession, project_id: UUID, user_id: UUID
) -> ParticipantRoleApi | None:
    """Devuelve el rol API del usuario en el proyecto, o None."""
    role = await db.scalar(
        select(Participacion.rol).where(
            Participacion.proyecto_id == project_id,
            Participacion.usuario_id == user_id,
        )
    )
    if role is None:
        return None
    return PARTICIPANT_ROLE_DB_TO_API[role]


async def create_milestone(
    db: AsyncSession, project: Proyecto, payload: MilestoneCreate
) -> Hito:
    """Crea un hito en la posición indicada y reordena los siguientes."""
    name = payload.name.strip()
    if not name:
        raise AppError(
            "MILESTONE_NAME_REQUIRED",
            "El Hito debe tener un nombre.",
            422,
        )

    await db.execute(
        select(Proyecto.id).where(Proyecto.id == project.id).with_for_update()
    )

    count = (
        await db.scalar(
            select(func.count(Hito.id)).where(Hito.proyecto_id == project.id)
        )
    ) or 0

    if payload.position < 1 or payload.position > count + 1:
        raise AppError(
            "INVALID_POSITION",
            "La posición del hito no es válida.",
            422,
        )

    affected = (
        await db.scalars(
            select(Hito)
            .where(
                Hito.proyecto_id == project.id,
                Hito.orden >= payload.position,
            )
            .order_by(Hito.orden.desc())
            .with_for_update()
        )
    ).all()

    for milestone in affected:
        milestone.orden += 1
        await db.flush()

    milestone = Hito(
        proyecto_id=project.id,
        nombre=name,
        orden=payload.position,
        estado=MilestoneStatus.PENDING,
    )
    db.add(milestone)
    _touch_project(project, datetime.now(UTC))

    await db.commit()
    await db.refresh(milestone)
    return milestone
