from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.modules.auth.models import Usuario
from app.modules.deliverables.dependencies import (
    DeliverableContext,
    FileContext,
    MilestoneContext,
    get_deliverable_collaborator_context,
    get_deliverable_context,
    get_deliverable_manager_context,
    get_file_context,
    get_milestone_manager_context,
)
from app.modules.deliverables.schemas import (
    DeliverableCreate,
    DeliverableDetail,
    DeliverableUpdate,
    ForumMessageResponse,
    MessageCreate,
    PendingReviewResponse,
    ReviewCreate,
    ReviewResponse,
    SubmissionResponse,
)
from app.modules.deliverables.service import (
    build_deliverable_detail,
    create_deliverable,
    is_latest_submission,
    list_pending_reviews,
    list_submission_responses,
    post_message,
    review_deliverable,
    serialize_message,
    serialize_review,
    serialize_submission,
    submit_deliverable,
    update_deliverable,
)
from app.modules.projects.enums import ParticipantRole
from app.modules.storage.service import get_storage

router = APIRouter(tags=["deliverables"])


@router.post(
    "/milestones/{milestone_id}/deliverables",
    response_model=DeliverableDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_deliverable_endpoint(
    payload: DeliverableCreate,
    context: Annotated[MilestoneContext, Depends(get_milestone_manager_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliverableDetail:
    """Crea un entregable dentro de un hito."""
    deliverable = await create_deliverable(
        db,
        context.project,
        context.milestone,
        payload,
        context.user,
    )
    detail_context = DeliverableContext(
        deliverable=deliverable,
        milestone=context.milestone,
        project=context.project,
        participation=context.participation,
        user=context.user,
    )
    return await build_deliverable_detail(db, detail_context)


@router.patch(
    "/deliverables/{deliverable_id}",
    response_model=DeliverableDetail,
)
async def update_deliverable_endpoint(
    payload: DeliverableUpdate,
    context: Annotated[DeliverableContext, Depends(get_deliverable_manager_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliverableDetail:
    """Edita un entregable existente."""
    await update_deliverable(db, context, payload)
    return await build_deliverable_detail(db, context)


@router.get(
    "/deliverables/{deliverable_id}",
    response_model=DeliverableDetail,
)
async def get_deliverable_endpoint(
    context: Annotated[DeliverableContext, Depends(get_deliverable_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliverableDetail:
    """Devuelve el detalle de un entregable a un participante."""
    return await build_deliverable_detail(db, context)


@router.get(
    "/deliverables/{deliverable_id}/submissions",
    response_model=list[SubmissionResponse],
)
async def list_submissions_endpoint(
    context: Annotated[DeliverableContext, Depends(get_deliverable_manager_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SubmissionResponse]:
    """Devuelve el historial completo de versiones a un gestor."""
    return await list_submission_responses(db, context)


@router.post(
    "/deliverables/{deliverable_id}/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_deliverable_endpoint(
    context: Annotated[
        DeliverableContext, Depends(get_deliverable_collaborator_context)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    files: Annotated[list[UploadFile] | None, File()] = None,
    link_url: Annotated[str | None, Form()] = None,
) -> SubmissionResponse:
    """Registra una nueva versión de un entregable."""
    submission = await submit_deliverable(db, context, files or [], link_url)
    return await serialize_submission(db, submission)


@router.post(
    "/deliverables/{deliverable_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def review_deliverable_endpoint(
    payload: ReviewCreate,
    context: Annotated[DeliverableContext, Depends(get_deliverable_manager_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewResponse:
    """Registra la decisión de un gestor sobre la última entrega."""
    review = await review_deliverable(db, context, payload)
    return await serialize_review(db, review)


@router.post(
    "/deliverables/{deliverable_id}/messages",
    response_model=ForumMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_message_endpoint(
    payload: MessageCreate,
    context: Annotated[DeliverableContext, Depends(get_deliverable_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ForumMessageResponse:
    """Publica un mensaje en el foro del entregable."""
    comment = await post_message(db, context, payload)
    return await serialize_message(db, comment)


@router.get(
    "/reviews/pending",
    response_model=list[PendingReviewResponse],
)
async def list_pending_reviews_endpoint(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PendingReviewResponse]:
    """Lista las entregas que esperan la revisión del gestor."""
    return await list_pending_reviews(db, current_user)


@router.get("/files/{file_id}/download")
async def download_file_endpoint(
    context: Annotated[FileContext, Depends(get_file_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """Descarga un archivo respetando el acceso por rol y versión."""
    if (
        context.participation.rol == ParticipantRole.COLLABORATOR
        and not await is_latest_submission(
            db, context.deliverable.id, context.submission.id
        )
    ):
        raise AppError(
            "FORBIDDEN",
            "Solo puedes descargar la última versión del entregable.",
            403,
        )

    path = get_storage().path(context.file.clave_almacenamiento)
    if not path.is_file():
        raise AppError(
            "FILE_NOT_FOUND",
            "El archivo no está disponible.",
            404,
        )

    return FileResponse(
        path,
        media_type=context.file.tipo_mime,
        filename=context.file.nombre,
    )
