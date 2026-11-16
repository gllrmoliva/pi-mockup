from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.modules.auth.models import Usuario
from app.modules.projects.dependencies import (
    ProjectContext,
    get_manager_context,
    get_project_context,
)
from app.modules.projects.schemas import (
    PARTICIPANT_ROLE_DB_TO_API,
    MilestoneCreate,
    MilestoneResponse,
    ProjectCreate,
    ProjectDetail,
    ProjectListItem,
    ProjectUpdate,
)
from app.modules.projects.service import (
    build_project_detail,
    create_milestone,
    create_project,
    get_participation_role,
    list_projects_for_user,
    update_project,
)

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectListItem])
async def list_projects(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProjectListItem]:
    """Lista los proyectos en los que participa el usuario."""
    return await list_projects_for_user(db, current_user)


@router.post(
    "/projects",
    response_model=ProjectDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_endpoint(
    payload: ProjectCreate,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetail:
    """Crea un proyecto; el profesor creador queda como gestor."""
    project = await create_project(db, current_user, payload)
    return await build_project_detail(db, project, "manager")


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project_endpoint(
    context: Annotated[ProjectContext, Depends(get_project_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetail:
    """Devuelve el detalle de un proyecto al que el usuario pertenece."""
    return await build_project_detail(
        db,
        context.project,
        PARTICIPANT_ROLE_DB_TO_API[context.participation.rol],
    )


@router.patch("/projects/{project_id}", response_model=ProjectDetail)
async def update_project_endpoint(
    payload: ProjectUpdate,
    context: Annotated[ProjectContext, Depends(get_manager_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetail:
    """Edita la información y los participantes de un proyecto."""
    project = await update_project(db, context.project, payload)
    my_role = await get_participation_role(db, project.id, context.user.id)
    return await build_project_detail(db, project, my_role)


@router.post(
    "/projects/{project_id}/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_milestone_endpoint(
    payload: MilestoneCreate,
    context: Annotated[ProjectContext, Depends(get_manager_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MilestoneResponse:
    """Crea un hito en la posición indicada dentro del proyecto."""
    milestone = await create_milestone(db, context.project, payload)
    return MilestoneResponse(
        id=milestone.id,
        name=milestone.nombre,
        order_index=milestone.orden,
        deliverables=[],
    )
