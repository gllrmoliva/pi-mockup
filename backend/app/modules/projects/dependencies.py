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
from app.modules.projects.enums import ParticipantRole
from app.modules.projects.models import Participacion, Proyecto

PROJECT_NOT_FOUND_MESSAGE = "No encontrado o no tienes acceso a este proyecto."
MANAGER_REQUIRED_MESSAGE = "Solo un gestor del proyecto puede realizar esta acción."


@dataclass(frozen=True)
class ProjectContext:
    """Proyecto, participación y usuario autenticado de una request."""

    project: Proyecto
    participation: Participacion
    user: Usuario


async def get_project_context(
    project_id: UUID,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectContext:
    """Carga un proyecto solo si el usuario participa en él."""
    participation = await db.scalar(
        select(Participacion).where(
            Participacion.proyecto_id == project_id,
            Participacion.usuario_id == current_user.id,
        )
    )
    if participation is None:
        raise AppError("PROJECT_NOT_FOUND", PROJECT_NOT_FOUND_MESSAGE, 404)

    project = await db.get(Proyecto, project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", PROJECT_NOT_FOUND_MESSAGE, 404)

    return ProjectContext(
        project=project,
        participation=participation,
        user=current_user,
    )


async def get_manager_context(
    context: Annotated[ProjectContext, Depends(get_project_context)],
) -> ProjectContext:
    """Exige que el usuario sea gestor del proyecto."""
    if context.participation.rol != ParticipantRole.MANAGER:
        raise AppError("FORBIDDEN", MANAGER_REQUIRED_MESSAGE, 403)
    return context
