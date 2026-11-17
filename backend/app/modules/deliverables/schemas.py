from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.modules.deliverables.enums import ForumMessageType, ReviewDecision
from app.modules.projects.schemas import (
    DeliverableStatusApi,
    ParticipantRoleApi,
    ReviewDecisionApi,
)
from app.modules.storage.enums import FileFormat

ForumMessageKindApi = Literal["user", "system"]

REVIEW_DECISION_API_TO_DB: dict[ReviewDecisionApi, ReviewDecision] = {
    "approved": ReviewDecision.APPROVED,
    "changes_requested": ReviewDecision.CHANGES_REQUESTED,
}
FORUM_MESSAGE_TYPE_DB_TO_API: dict[ForumMessageType, ForumMessageKindApi] = {
    ForumMessageType.USER: "user",
    ForumMessageType.SYSTEM: "system",
}


class DeliverableCreate(BaseModel):
    """Datos para crear un entregable."""

    title: str = Field(max_length=200)
    description: str = Field(max_length=4000)
    deadline_at: AwareDatetime
    allowed_formats: list[FileFormat]
    max_file_size_mb: int = Field(default=50, ge=1, le=200)

    model_config = ConfigDict(extra="forbid")


class DeliverableUpdate(BaseModel):
    """Datos editables de un entregable."""

    title: str = Field(max_length=200)
    description: str = Field(max_length=4000)
    deadline_at: AwareDatetime
    allowed_formats: list[FileFormat]
    max_file_size_mb: int = Field(default=50, ge=1, le=200)

    model_config = ConfigDict(extra="forbid")


class MessageCreate(BaseModel):
    """Mensaje del foro de un entregable."""

    body: str = Field(max_length=2000)

    model_config = ConfigDict(extra="forbid")


class SubmissionFileResponse(BaseModel):
    """Archivo adjunto a una entrega o a una revisión."""

    id: UUID
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str


class ReviewResponse(BaseModel):
    """Revisión de una entrega y sus archivos adjuntos."""

    id: UUID
    decision: ReviewDecisionApi
    reviewer_name: str
    reviewed_at: datetime
    files: list[SubmissionFileResponse]


class SubmissionResponse(BaseModel):
    """Versión concreta de una entrega."""

    id: UUID
    version: int
    submitted_at: datetime
    link_url: str | None
    author_id: UUID
    author_name: str
    files: list[SubmissionFileResponse]
    review: ReviewResponse | None


class ForumMessageResponse(BaseModel):
    """Mensaje de usuario o evento automático del foro de un entregable."""

    id: UUID
    kind: ForumMessageKindApi
    body: str
    author_id: UUID | None
    author_name: str | None
    created_at: datetime


class PendingReviewResponse(BaseModel):
    """Entregable que espera la revisión de un gestor."""

    deliverable_id: UUID
    title: str
    project_id: UUID
    project_topic: str
    milestone_name: str
    collaborator_name: str
    version: int
    submitted_at: datetime


class DeliverableDetail(BaseModel):
    """Detalle de un entregable y su historial visible."""

    id: UUID
    project_id: UUID
    project_topic: str
    milestone_id: UUID
    milestone_name: str
    title: str
    description: str
    deadline_at: datetime
    allowed_formats: list[str]
    max_file_size_mb: int
    status: DeliverableStatusApi
    is_overdue: bool
    version_count: int
    my_role: ParticipantRoleApi
    latest_submission: SubmissionResponse | None
    review: ReviewResponse | None
    messages: list[ForumMessageResponse]
