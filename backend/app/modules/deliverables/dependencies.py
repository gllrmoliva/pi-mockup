from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.modules.auth.models import Usuario
from app.modules.deliverables.models import Entrega, Entregable, Revision
from app.modules.projects.enums import ParticipantRole
from app.modules.projects.models import Hito, Participacion, Proyecto
from app.modules.storage.models import Archivo

DELIVERABLE_NOT_FOUND_MESSAGE = "No encontrado o no tienes acceso a este entregable."
MILESTONE_NOT_FOUND_MESSAGE = "No encontrado o no tienes acceso a este hito."
MANAGER_REQUIRED_MESSAGE = "Solo un gestor del proyecto puede realizar esta acción."
COLLABORATOR_REQUIRED_MESSAGE = (
    "Solo un colaborador del proyecto puede realizar esta acción."
)
FILE_NOT_FOUND_MESSAGE = "No encontrado o no tienes acceso a este archivo."


@dataclass(frozen=True)
class MilestoneContext:
    """Hito, proyecto y participación del usuario autenticado."""

    milestone: Hito
    project: Proyecto
    participation: Participacion
    user: Usuario


@dataclass(frozen=True)
class DeliverableContext:
    """Entregable, hito, proyecto y participación del usuario."""

    deliverable: Entregable
    milestone: Hito
    project: Proyecto
    participation: Participacion
    user: Usuario


@dataclass(frozen=True)
class FileContext:
    """Archivo, entrega o revisión, entregable y participación del usuario."""

    file: Archivo
    submission: Entrega
    review: Revision | None
    deliverable: Entregable
    milestone: Hito
    project: Proyecto
    participation: Participacion
    user: Usuario


async def get_milestone_manager_context(
    milestone_id: UUID,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MilestoneContext:
    """Carga un hito y exige que el usuario sea gestor del proyecto."""
    milestone = await db.get(Hito, milestone_id)
    if milestone is None:
        raise AppError("MILESTONE_NOT_FOUND", MILESTONE_NOT_FOUND_MESSAGE, 404)

    project = await db.get(Proyecto, milestone.proyecto_id)
    if project is None:
        raise AppError("MILESTONE_NOT_FOUND", MILESTONE_NOT_FOUND_MESSAGE, 404)

    participation = await db.scalar(
        select(Participacion).where(
            Participacion.proyecto_id == project.id,
            Participacion.usuario_id == current_user.id,
        )
    )
    if participation is None:
        raise AppError("MILESTONE_NOT_FOUND", MILESTONE_NOT_FOUND_MESSAGE, 404)

    if participation.rol != ParticipantRole.MANAGER:
        raise AppError("FORBIDDEN", MANAGER_REQUIRED_MESSAGE, 403)

    return MilestoneContext(
        milestone=milestone,
        project=project,
        participation=participation,
        user=current_user,
    )


async def get_deliverable_context(
    deliverable_id: UUID,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliverableContext:
    """Carga un entregable solo si el usuario participa en su proyecto."""
    deliverable = await db.get(Entregable, deliverable_id)
    if deliverable is None:
        raise AppError("DELIVERABLE_NOT_FOUND", DELIVERABLE_NOT_FOUND_MESSAGE, 404)

    milestone = await db.get(Hito, deliverable.hito_id)
    if milestone is None:
        raise AppError("DELIVERABLE_NOT_FOUND", DELIVERABLE_NOT_FOUND_MESSAGE, 404)

    project = await db.get(Proyecto, milestone.proyecto_id)
    if project is None:
        raise AppError("DELIVERABLE_NOT_FOUND", DELIVERABLE_NOT_FOUND_MESSAGE, 404)

    participation = await db.scalar(
        select(Participacion).where(
            Participacion.proyecto_id == project.id,
            Participacion.usuario_id == current_user.id,
        )
    )
    if participation is None:
        raise AppError("DELIVERABLE_NOT_FOUND", DELIVERABLE_NOT_FOUND_MESSAGE, 404)

    return DeliverableContext(
        deliverable=deliverable,
        milestone=milestone,
        project=project,
        participation=participation,
        user=current_user,
    )


async def get_deliverable_manager_context(
    context: Annotated[DeliverableContext, Depends(get_deliverable_context)],
) -> DeliverableContext:
    """Exige que el usuario sea gestor del proyecto del entregable."""
    if context.participation.rol != ParticipantRole.MANAGER:
        raise AppError("FORBIDDEN", MANAGER_REQUIRED_MESSAGE, 403)
    return context


async def get_deliverable_collaborator_context(
    context: Annotated[DeliverableContext, Depends(get_deliverable_context)],
) -> DeliverableContext:
    """Exige que el usuario sea colaborador del proyecto del entregable."""
    if context.participation.rol != ParticipantRole.COLLABORATOR:
        raise AppError("FORBIDDEN", COLLABORATOR_REQUIRED_MESSAGE, 403)
    return context


async def get_file_context(
    file_id: UUID,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileContext:
    """Carga un archivo y la participación del usuario en su proyecto."""
    file = await db.get(Archivo, file_id)
    if file is None:
        raise AppError("FILE_NOT_FOUND", FILE_NOT_FOUND_MESSAGE, 404)

    review: Revision | None = None
    if file.revision_id is not None:
        review = await db.get(Revision, file.revision_id)
        if review is None:
            raise AppError("FILE_NOT_FOUND", FILE_NOT_FOUND_MESSAGE, 404)
        submission = await db.get(Entrega, review.entrega_id)
    else:
        submission = (
            await db.get(Entrega, file.entrega_id)
            if file.entrega_id is not None
            else None
        )

    if submission is None:
        raise AppError("FILE_NOT_FOUND", FILE_NOT_FOUND_MESSAGE, 404)

    deliverable = await db.get(Entregable, submission.entregable_id)
    if deliverable is None:
        raise AppError("FILE_NOT_FOUND", FILE_NOT_FOUND_MESSAGE, 404)

    milestone = await db.get(Hito, deliverable.hito_id)
    if milestone is None:
        raise AppError("FILE_NOT_FOUND", FILE_NOT_FOUND_MESSAGE, 404)

    project = await db.get(Proyecto, milestone.proyecto_id)
    if project is None:
        raise AppError("FILE_NOT_FOUND", FILE_NOT_FOUND_MESSAGE, 404)

    participation = await db.scalar(
        select(Participacion).where(
            Participacion.proyecto_id == project.id,
            Participacion.usuario_id == current_user.id,
        )
    )
    if participation is None:
        raise AppError("FILE_NOT_FOUND", FILE_NOT_FOUND_MESSAGE, 404)

    return FileContext(
        file=file,
        submission=submission,
        review=review,
        deliverable=deliverable,
        milestone=milestone,
        project=project,
        participation=participation,
        user=current_user,
    )
