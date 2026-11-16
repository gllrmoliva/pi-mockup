export type UserType = 'professor' | 'student';
export type UserState = 'invited' | 'active';
export type ProjectType = 'memoir' | 'thesis' | 'research';
export type ProjectStatus = 'active' | 'closed';
export type ParticipantRole = 'manager' | 'collaborator';
export type DeliverableStatus = 'pending' | 'submitted' | 'changes_requested' | 'approved';
export type ReviewDecision = 'approved' | 'changes_requested';
export type FileFormat = 'pdf' | 'zip' | 'docx';

export type User = {
    id: string;
    name: string;
    email: string;
    user_type: UserType;
    state: UserState;
};

export type Participant = {
    id: string;
    name: string;
    email: string;
    role: ParticipantRole;
};

export type LatestSubmissionSummary = {
    version: number;
    submitted_at: string;
    author_name: string;
};

export type ReviewSummary = {
    decision: ReviewDecision;
    reviewer_name: string;
    reviewed_at: string;
};

export type DeliverableSummary = {
    id: string;
    title: string;
    deadline_at: string;
    status: DeliverableStatus;
    is_overdue: boolean;
    latest_submission: LatestSubmissionSummary | null;
    review: ReviewSummary | null;
};

export type Milestone = {
    id: string;
    name: string;
    order_index: number;
    deliverables: DeliverableSummary[];
};

export type ProjectListItem = {
    id: string;
    topic: string;
    project_type: ProjectType;
    status: ProjectStatus;
    started_on: string;
    last_modified_at: string;
    my_role: ParticipantRole;
    participants: Participant[];
    total_deliverables: number;
    approved_deliverables: number;
    overdue_deliverables: number;
    pending_review_deliverables: number;
    next_deadline_at: string | null;
};

export type ProjectDetail = {
    id: string;
    topic: string;
    project_type: ProjectType;
    status: ProjectStatus;
    started_on: string;
    last_modified_at: string;
    my_role: ParticipantRole | null;
    participants: Participant[];
    milestones: Milestone[];
};

export type SubmissionFile = {
    id: string;
    original_name: string;
    mime_type: string;
    size_bytes: number;
    sha256: string;
};

export type Review = {
    id: string;
    decision: ReviewDecision;
    reviewer_name: string;
    reviewed_at: string;
};

export type Submission = {
    id: string;
    version: number;
    submitted_at: string;
    link_url: string | null;
    author_id: string;
    author_name: string;
    files: SubmissionFile[];
    review: Review | null;
};

export type ForumMessage = {
    id: string;
    body: string;
    author_id: string;
    author_name: string;
    created_at: string;
};

export type DeliverableDetail = {
    id: string;
    project_id: string;
    project_topic: string;
    milestone_id: string;
    milestone_name: string;
    title: string;
    description: string;
    deadline_at: string;
    allowed_formats: FileFormat[];
    max_file_size_mb: number;
    status: DeliverableStatus;
    is_overdue: boolean;
    version_count: number;
    my_role: ParticipantRole;
    latest_submission: Submission | null;
    review: Review | null;
    messages: ForumMessage[];
};

export type PendingReview = {
    deliverable_id: string;
    title: string;
    project_id: string;
    project_topic: string;
    milestone_name: string;
    collaborator_name: string;
    version: number;
    submitted_at: string;
};

export type ProjectInput = {
    topic: string;
    project_type: ProjectType;
    manager_emails: string[];
    collaborator_emails: string[];
};

export type MilestoneInput = {
    name: string;
    position: number;
};

export type DeliverableInput = {
    title: string;
    description: string;
    deadline_at: string;
    allowed_formats: FileFormat[];
    max_file_size_mb: number;
};
