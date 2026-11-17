import hashlib
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.auth.models import Usuario
from app.modules.deliverables.dependencies import DeliverableContext
from app.modules.deliverables.enums import DeliverableStatus, ForumMessageType
from app.modules.deliverables.models import (
    Comentario,
    Entrega,
    Entregable,
    Revision,
)
from app.modules.deliverables.schemas import (
    FORUM_MESSAGE_TYPE_DB_TO_API,
    REVIEW_DECISION_API_TO_DB,
    DeliverableCreate,
    DeliverableDetail,
    DeliverableUpdate,
    ForumMessageResponse,
    MessageCreate,
    PendingReviewResponse,
    ReviewCreate,
    ReviewResponse,
    SubmissionFileResponse,
    SubmissionResponse,
)
from app.modules.projects.enums import ParticipantRole
from app.modules.projects.models import Hito, Participacion, Proyecto
from app.modules.projects.schemas import (
    DELIVERABLE_STATUS_DB_TO_API,
    PARTICIPANT_ROLE_DB_TO_API,
    REVIEW_DECISION_DB_TO_API,
)
from app.modules.storage.models import Archivo
from app.modules.storage.service import get_storage

ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "zip": {
        "application/zip",
        "application/x-zip-compressed",
        "multipart/x-zip",
    },
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}
FIELDS_REQUIRED_MESSAGE = "Los campos no pueden estar vacíos."
INVALID_DEADLINE_MESSAGE = "Ingrese una fecha de entrega válida."


class _UploadStream:
    """Lee un UploadFile, calcula tamaño y SHA-256 y aplica el límite."""

    def __init__(self, upload: UploadFile, max_bytes: int) -> None:
        self.upload = upload
        self.max_bytes = max_bytes
        self.size = 0
        self.digest = hashlib.sha256()

    async def chunks(self) -> AsyncIterator[bytes]:
        while True:
            chunk = await self.upload.read(1024 * 1024)
            if not chunk:
                break
            self.size += len(chunk)
            if self.size > self.max_bytes:
                raise AppError(
                    "FILE_TOO_LARGE",
                    (
                        "El archivo "
                        f"{self.upload.filename or 'sin nombre'} supera el "
                        "tamaño máximo permitido."
                    ),
                    422,
                )
            self.digest.update(chunk)
            yield chunk


def _touch_project(project: Proyecto, now: datetime) -> None:
    project.fecha_ultima_modificacion = now
    project.modified_at = now


def _append_system_message(
    db: AsyncSession,
    deliverable_id: uuid.UUID,
    text: str,
    when: datetime,
) -> None:
    """Agrega un evento automático al foro del entregable."""
    db.add(
        Comentario(
            entregable_id=deliverable_id,
            autor_id=None,
            tipo=ForumMessageType.SYSTEM,
            texto=text,
            fecha=when,
        )
    )


def _validate_payload(
    payload: DeliverableCreate | DeliverableUpdate,
    now: datetime,
    *,
    current_deadline: datetime | None = None,
) -> tuple[str, str, datetime, list[str], int]:
    title = payload.title.strip()
    description = payload.description.strip()
    allowed_formats = [file_format.value for file_format in payload.allowed_formats]

    if not title or not description or not allowed_formats:
        raise AppError("DELIVERABLE_FIELDS_REQUIRED", FIELDS_REQUIRED_MESSAGE, 422)

    if current_deadline is None:
        if payload.deadline_at <= now:
            raise AppError("INVALID_DEADLINE", INVALID_DEADLINE_MESSAGE, 422)
    elif payload.deadline_at != current_deadline and payload.deadline_at <= now:
        raise AppError("INVALID_DEADLINE", INVALID_DEADLINE_MESSAGE, 422)

    return (
        title,
        description,
        payload.deadline_at,
        allowed_formats,
        payload.max_file_size_mb,
    )


def _validate_link(link_url: str | None) -> str | None:
    if link_url is None:
        return None
    normalized = link_url.strip()
    if not normalized:
        return None
    if len(normalized) > 2048 or not normalized.startswith("https://"):
        raise AppError(
            "INVALID_LINK",
            "Ingrese un enlace HTTPS válido.",
            422,
        )
    return normalized


def _validate_upload(
    upload: UploadFile,
    allowed_formats: list[str],
) -> str:
    filename = upload.filename
    if not filename:
        raise AppError(
            "INVALID_FILE_FORMAT",
            "El archivo no tiene un nombre válido.",
            422,
        )

    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in allowed_formats:
        raise AppError(
            "INVALID_FILE_FORMAT",
            f"El formato del archivo no está permitido: {filename}.",
            422,
        )

    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_MIME_TYPES.get(extension, set()):
        raise AppError(
            "INVALID_FILE_FORMAT",
            f"El tipo de archivo no está permitido: {filename}.",
            422,
        )

    return content_type


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


async def _latest_submission(
    db: AsyncSession, deliverable_id: uuid.UUID
) -> Entrega | None:
    return await db.scalar(
        select(Entrega)
        .where(Entrega.entregable_id == deliverable_id)
        .order_by(Entrega.version.desc())
        .limit(1)
    )


async def _version_count(db: AsyncSession, deliverable_id: uuid.UUID) -> int:
    count = await db.scalar(
        select(func.count(Entrega.id)).where(Entrega.entregable_id == deliverable_id)
    )
    return count or 0


def _file_response(file: Archivo) -> SubmissionFileResponse:
    return SubmissionFileResponse(
        id=file.id,
        original_name=file.nombre,
        mime_type=file.tipo_mime,
        size_bytes=file.tamano,
        sha256=file.sha256,
    )


async def serialize_review(db: AsyncSession, review: Revision) -> ReviewResponse:
    """Serializa una revisión con el nombre del gestor."""
    reviewer = await db.get(Usuario, review.gestor_id)
    return ReviewResponse(
        id=review.id,
        decision=REVIEW_DECISION_DB_TO_API[review.decision],
        reviewer_name=(
            reviewer.nombre if reviewer is not None else "Usuario eliminado"
        ),
        reviewed_at=review.fecha,
    )


async def serialize_submission(
    db: AsyncSession, submission: Entrega
) -> SubmissionResponse:
    """Serializa una entrega con sus archivos y revisión."""
    files = (
        await db.scalars(
            select(Archivo)
            .where(Archivo.entrega_id == submission.id)
            .order_by(Archivo.id)
        )
    ).all()
    review = await db.scalar(
        select(Revision).where(Revision.entrega_id == submission.id)
    )
    author = await db.get(Usuario, submission.autor_id)

    return SubmissionResponse(
        id=submission.id,
        version=submission.version,
        submitted_at=submission.fecha_envio,
        link_url=submission.enlace,
        author_id=submission.autor_id,
        author_name=author.nombre if author is not None else "Usuario eliminado",
        files=[_file_response(file) for file in files],
        review=await serialize_review(db, review) if review is not None else None,
    )


async def serialize_message(
    db: AsyncSession, comment: Comentario
) -> ForumMessageResponse:
    """Serializa un mensaje de usuario o un evento del foro."""
    author = (
        await db.get(Usuario, comment.autor_id)
        if comment.autor_id is not None
        else None
    )
    author_name: str | None = None
    if comment.tipo == ForumMessageType.USER:
        author_name = author.nombre if author is not None else "Usuario eliminado"

    return ForumMessageResponse(
        id=comment.id,
        kind=FORUM_MESSAGE_TYPE_DB_TO_API[comment.tipo],
        body=comment.texto,
        author_id=comment.autor_id,
        author_name=author_name,
        created_at=comment.fecha,
    )


async def build_deliverable_detail(
    db: AsyncSession, context: DeliverableContext
) -> DeliverableDetail:
    """Construye el detalle de un entregable para un participante."""
    deliverable = context.deliverable
    now = datetime.now(UTC)
    latest = await _latest_submission(db, deliverable.id)
    latest_response = (
        await serialize_submission(db, latest) if latest is not None else None
    )

    messages = (
        await db.scalars(
            select(Comentario)
            .where(Comentario.entregable_id == deliverable.id)
            .order_by(Comentario.fecha, Comentario.id)
        )
    ).all()

    return DeliverableDetail(
        id=deliverable.id,
        project_id=context.project.id,
        project_topic=context.project.tema,
        milestone_id=context.milestone.id,
        milestone_name=context.milestone.nombre,
        title=deliverable.titulo,
        description=deliverable.descripcion,
        deadline_at=deliverable.fecha_limite,
        allowed_formats=deliverable.formatos_admitidos,
        max_file_size_mb=deliverable.tamano_max_mb,
        status=DELIVERABLE_STATUS_DB_TO_API[deliverable.estado],
        is_overdue=await _is_overdue(db, deliverable, now),
        version_count=await _version_count(db, deliverable.id),
        my_role=PARTICIPANT_ROLE_DB_TO_API[context.participation.rol],
        latest_submission=latest_response,
        review=(latest_response.review if latest_response is not None else None),
        messages=[await serialize_message(db, message) for message in messages],
    )


async def create_deliverable(
    db: AsyncSession,
    project: Proyecto,
    milestone: Hito,
    payload: DeliverableCreate,
    actor: Usuario,
) -> Entregable:
    """Crea un entregable dentro de un hito."""
    now = datetime.now(UTC)
    title, description, deadline, formats, max_size_mb = _validate_payload(payload, now)

    deliverable = Entregable(
        hito_id=milestone.id,
        titulo=title,
        descripcion=description,
        fecha_limite=deadline,
        formatos_admitidos=formats,
        tamano_max_mb=max_size_mb,
        estado=DeliverableStatus.PENDING,
    )
    db.add(deliverable)
    await db.flush()
    _append_system_message(
        db,
        deliverable.id,
        f"{actor.nombre} ha creado el entregable.",
        now,
    )
    _touch_project(project, now)

    await db.commit()
    await db.refresh(deliverable)
    return deliverable


async def update_deliverable(
    db: AsyncSession,
    context: DeliverableContext,
    payload: DeliverableUpdate,
) -> Entregable:
    """Edita un entregable, respetando la regla de fechas pasadas."""
    now = datetime.now(UTC)
    title, description, deadline, formats, max_size_mb = _validate_payload(
        payload,
        now,
        current_deadline=context.deliverable.fecha_limite,
    )

    deliverable = context.deliverable
    deliverable.titulo = title
    deliverable.descripcion = description
    deliverable.fecha_limite = deadline
    deliverable.formatos_admitidos = formats
    deliverable.tamano_max_mb = max_size_mb
    _append_system_message(
        db,
        deliverable.id,
        f"{context.user.nombre} ha editado el entregable.",
        now,
    )
    _touch_project(context.project, now)

    await db.commit()
    await db.refresh(deliverable)
    return deliverable


async def submit_deliverable(
    db: AsyncSession,
    context: DeliverableContext,
    files: list[UploadFile],
    link_url: str | None,
) -> Entrega:
    """Registra una nueva versión inmutable de un entregable."""
    normalized_link = _validate_link(link_url)
    if not files and normalized_link is None:
        raise AppError(
            "NO_FILES_OR_LINK",
            "Adjunta al menos un archivo o ingresa un enlace HTTPS válido.",
            422,
        )

    locked = await db.scalar(
        select(Entregable)
        .where(Entregable.id == context.deliverable.id)
        .with_for_update()
    )
    if locked is None:
        raise AppError(
            "DELIVERABLE_NOT_FOUND",
            "No encontrado o no tienes acceso a este entregable.",
            404,
        )

    if locked.estado == DeliverableStatus.APPROVED:
        raise AppError(
            "SUBMISSION_NOT_ALLOWED",
            "El entregable ya está aprobado y no admite nuevas entregas.",
            409,
        )

    allowed_formats = locked.formatos_admitidos
    content_types = [_validate_upload(upload, allowed_formats) for upload in files]
    max_bytes = locked.tamano_max_mb * 1024 * 1024

    max_version = (
        await db.scalar(
            select(func.max(Entrega.version)).where(Entrega.entregable_id == locked.id)
        )
    ) or 0

    submission = Entrega(
        entregable_id=locked.id,
        version=max_version + 1,
        autor_id=context.user.id,
        enlace=normalized_link,
    )
    db.add(submission)
    await db.flush()
    _append_system_message(
        db,
        locked.id,
        f"{context.user.nombre} ha entregado la versión {submission.version}.",
        datetime.now(UTC),
    )

    storage = get_storage()
    saved_keys: list[str] = []

    try:
        for upload, content_type in zip(files, content_types, strict=True):
            key = (
                f"projects/{context.project.id}/deliverables/{locked.id}/"
                f"submissions/{submission.id}/{uuid.uuid4().hex}"
            )
            stream = _UploadStream(upload, max_bytes)
            await storage.save(key, stream.chunks())
            saved_keys.append(key)
            if stream.size == 0:
                raise AppError(
                    "EMPTY_FILE",
                    f"El archivo {upload.filename or 'sin nombre'} está vacío.",
                    422,
                )
            db.add(
                Archivo(
                    entrega_id=submission.id,
                    nombre=upload.filename or "archivo",
                    tipo_mime=content_type,
                    tamano=stream.size,
                    clave_almacenamiento=key,
                    sha256=stream.digest.hexdigest(),
                )
            )

        locked.estado = DeliverableStatus.SUBMITTED
        _touch_project(context.project, datetime.now(UTC))
        await db.commit()
    except Exception:
        await db.rollback()
        for key in saved_keys:
            await storage.delete(key)
        raise

    await db.refresh(submission)
    return submission


async def review_deliverable(
    db: AsyncSession,
    context: DeliverableContext,
    payload: ReviewCreate,
) -> Revision:
    """Registra la decisión de un gestor sobre la última entrega."""
    locked = await db.scalar(
        select(Entregable)
        .where(Entregable.id == context.deliverable.id)
        .with_for_update()
    )
    if locked is None:
        raise AppError(
            "DELIVERABLE_NOT_FOUND",
            "No encontrado o no tienes acceso a este entregable.",
            404,
        )

    latest = await db.scalar(
        select(Entrega)
        .where(Entrega.entregable_id == locked.id)
        .order_by(Entrega.version.desc())
        .limit(1)
        .with_for_update()
    )
    if latest is None:
        raise AppError(
            "REVIEW_NOT_ALLOWED",
            "El entregable debe tener al menos una entrega.",
            409,
        )

    if locked.estado != DeliverableStatus.SUBMITTED:
        raise AppError(
            "REVIEW_NOT_ALLOWED",
            "El entregable no está pendiente de revisión.",
            409,
        )

    existing_review = await db.scalar(
        select(Revision).where(Revision.entrega_id == latest.id)
    )
    if existing_review is not None:
        raise AppError(
            "REVIEW_NOT_ALLOWED",
            "La última entrega ya fue revisada.",
            409,
        )

    decision = REVIEW_DECISION_API_TO_DB[payload.decision]
    review = Revision(
        entrega_id=latest.id,
        gestor_id=context.user.id,
        decision=decision,
    )
    db.add(review)

    locked.estado = (
        DeliverableStatus.APPROVED
        if payload.decision == "approved"
        else DeliverableStatus.CHANGES_REQUESTED
    )
    now = datetime.now(UTC)
    if payload.decision == "approved":
        event_text = (
            f"{context.user.nombre} ha marcado la versión "
            f"{latest.version} como Aprobada."
        )
    else:
        event_text = (
            f"{context.user.nombre} ha solicitado cambios en la versión "
            f"{latest.version}."
        )
    _append_system_message(db, locked.id, event_text, now)
    _touch_project(context.project, now)

    await db.commit()
    await db.refresh(review)
    return review


async def post_message(
    db: AsyncSession,
    context: DeliverableContext,
    payload: MessageCreate,
) -> Comentario:
    """Publica un mensaje en el foro del entregable."""
    body = payload.body.strip()
    if not body:
        raise AppError(
            "MESSAGE_EMPTY",
            "El comentario no puede estar vacío.",
            422,
        )

    comment = Comentario(
        entregable_id=context.deliverable.id,
        autor_id=context.user.id,
        tipo=ForumMessageType.USER,
        texto=body,
    )
    db.add(comment)
    _touch_project(context.project, datetime.now(UTC))

    await db.commit()
    await db.refresh(comment)
    return comment


async def list_submission_responses(
    db: AsyncSession, context: DeliverableContext
) -> list[SubmissionResponse]:
    """Lista todas las versiones de un entregable para un gestor."""
    submissions = (
        await db.scalars(
            select(Entrega)
            .where(Entrega.entregable_id == context.deliverable.id)
            .order_by(Entrega.version)
        )
    ).all()
    return [await serialize_submission(db, submission) for submission in submissions]


async def is_latest_submission(
    db: AsyncSession, deliverable_id: uuid.UUID, submission_id: uuid.UUID
) -> bool:
    """Indica si una entrega es la última versión del entregable."""
    latest = await _latest_submission(db, deliverable_id)
    return latest is not None and latest.id == submission_id


async def list_pending_reviews(
    db: AsyncSession, user: Usuario
) -> list[PendingReviewResponse]:
    """Lista entregables entregados que esperan al gestor autenticado."""
    deliverables = (
        await db.scalars(
            select(Entregable)
            .join(Hito, Entregable.hito_id == Hito.id)
            .join(Proyecto, Hito.proyecto_id == Proyecto.id)
            .join(
                Participacion,
                Participacion.proyecto_id == Proyecto.id,
            )
            .where(
                Participacion.usuario_id == user.id,
                Participacion.rol == ParticipantRole.MANAGER,
                Entregable.estado == DeliverableStatus.SUBMITTED,
            )
        )
    ).all()

    result: list[PendingReviewResponse] = []
    for deliverable in deliverables:
        latest = await _latest_submission(db, deliverable.id)
        if latest is None:
            continue

        milestone = await db.get(Hito, deliverable.hito_id)
        if milestone is None:
            continue

        project = await db.get(Proyecto, milestone.proyecto_id)
        if project is None:
            continue

        author = await db.get(Usuario, latest.autor_id)
        result.append(
            PendingReviewResponse(
                deliverable_id=deliverable.id,
                title=deliverable.titulo,
                project_id=project.id,
                project_topic=project.tema,
                milestone_name=milestone.nombre,
                collaborator_name=(
                    author.nombre if author is not None else "Usuario eliminado"
                ),
                version=latest.version,
                submitted_at=latest.fecha_envio,
            )
        )

    result.sort(key=lambda item: item.submitted_at)
    return result
