from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.deliverables.enums import DeliverableStatus, ReviewDecision
from app.modules.projects.enums import ParticipantRole, ProjectStatus, ProjectType

ProjectTypeApi = Literal["memoir", "thesis", "research"]
ProjectStatusApi = Literal["active", "closed"]
ParticipantRoleApi = Literal["manager", "collaborator"]
DeliverableStatusApi = Literal["pending", "submitted", "changes_requested", "approved"]
ReviewDecisionApi = Literal["approved", "changes_requested"]

PROJECT_TYPE_API_TO_DB: dict[ProjectTypeApi, ProjectType] = {
    "memoir": ProjectType.MEMOIR,
    "thesis": ProjectType.THESIS,
    "research": ProjectType.RESEARCH,
}
PROJECT_TYPE_DB_TO_API: dict[ProjectType, ProjectTypeApi] = {
    ProjectType.MEMOIR: "memoir",
    ProjectType.THESIS: "thesis",
    ProjectType.RESEARCH: "research",
}
PROJECT_STATUS_DB_TO_API: dict[ProjectStatus, ProjectStatusApi] = {
    ProjectStatus.ACTIVE: "active",
    ProjectStatus.CLOSED: "closed",
}
PARTICIPANT_ROLE_DB_TO_API: dict[ParticipantRole, ParticipantRoleApi] = {
    ParticipantRole.MANAGER: "manager",
    ParticipantRole.COLLABORATOR: "collaborator",
}
DELIVERABLE_STATUS_DB_TO_API: dict[DeliverableStatus, DeliverableStatusApi] = {
    DeliverableStatus.PENDING: "pending",
    DeliverableStatus.SUBMITTED: "submitted",
    DeliverableStatus.CHANGES_REQUESTED: "changes_requested",
    DeliverableStatus.APPROVED: "approved",
}
REVIEW_DECISION_DB_TO_API: dict[ReviewDecision, ReviewDecisionApi] = {
    ReviewDecision.APPROVED: "approved",
    ReviewDecision.CHANGES_REQUESTED: "changes_requested",
}


class ProjectCreate(BaseModel):
    """Datos para crear un proyecto."""

    topic: str = Field(max_length=300)
    project_type: ProjectTypeApi
    manager_emails: list[EmailStr] = Field(default_factory=list)
    collaborator_emails: list[EmailStr] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ProjectUpdate(BaseModel):
    """Datos editables de un proyecto."""

    topic: str = Field(max_length=300)
    project_type: ProjectTypeApi
    manager_emails: list[EmailStr] = Field(default_factory=list)
    collaborator_emails: list[EmailStr] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class MilestoneCreate(BaseModel):
    """Datos para crear un hito."""

    name: str = Field(max_length=200)
    position: int

    model_config = ConfigDict(extra="forbid")


class ParticipantResponse(BaseModel):
    """Participante de un proyecto."""

    id: UUID
    name: str
    email: str
    role: ParticipantRoleApi


class LatestSubmissionResponse(BaseModel):
    """Resumen de la última entrega de un entregable."""

    version: int
    submitted_at: datetime
    author_name: str


class ReviewSummary(BaseModel):
    """Resumen de la revisión de una entrega."""

    decision: ReviewDecisionApi
    reviewer_name: str
    reviewed_at: datetime


class DeliverableSummary(BaseModel):
    """Entregable dentro del detalle de un proyecto."""

    id: UUID
    title: str
    deadline_at: datetime
    status: DeliverableStatusApi
    is_overdue: bool
    latest_submission: LatestSubmissionResponse | None
    review: ReviewSummary | None


class MilestoneResponse(BaseModel):
    """Hito con sus entregables."""

    id: UUID
    name: str
    order_index: int
    deliverables: list[DeliverableSummary]


class ProjectListItem(BaseModel):
    """Resumen de un proyecto en el portafolio."""

    id: UUID
    topic: str
    project_type: ProjectTypeApi
    status: ProjectStatusApi
    started_on: date
    last_modified_at: datetime
    my_role: ParticipantRoleApi
    participants: list[ParticipantResponse]
    total_deliverables: int
    approved_deliverables: int
    overdue_deliverables: int
    pending_review_deliverables: int
    next_deadline_at: datetime | None


class ProjectDetail(BaseModel):
    """Detalle completo de un proyecto."""

    id: UUID
    topic: str
    project_type: ProjectTypeApi
    status: ProjectStatusApi
    started_on: date
    last_modified_at: datetime
    my_role: ParticipantRoleApi | None
    participants: list[ParticipantResponse]
    milestones: list[MilestoneResponse]
