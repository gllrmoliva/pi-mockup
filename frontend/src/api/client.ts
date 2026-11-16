import type {
    DeliverableDetail,
    DeliverableInput,
    ForumMessage,
    Milestone,
    MilestoneInput,
    PendingReview,
    ProjectDetail,
    ProjectInput,
    ProjectListItem,
    Review,
    ReviewDecision,
    Submission,
    User,
} from './types';

export class ApiError extends Error {
    readonly status: number;
    readonly code: string | null;

    constructor(message: string, status: number, code: string | null = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
    }
}

type ErrorPayload = {
    error?: {
        code?: string;
        message?: string;
    };
    detail?: unknown;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(path, {
        credentials: 'include',
        ...init,
    });

    if (response.status === 204) {
        return undefined as T;
    }

    const payload = (await response.json().catch(() => null)) as unknown;

    if (!response.ok) {
        if (response.status === 401 && !path.startsWith('/api/v1/auth/')) {
            window.dispatchEvent(new Event('hito:session-expired'));
        }

        const errorPayload = payload as ErrorPayload | null;
        const message =
            errorPayload?.error?.message ??
            (Array.isArray(errorPayload?.detail)
                ? 'Revisa los datos ingresados.'
                : `No se pudo completar la solicitud (${response.status}).`);

        throw new ApiError(message, response.status, errorPayload?.error?.code ?? null);
    }

    return payload as T;
}

function jsonRequest<T>(path: string, method: string, body: unknown): Promise<T> {
    return request<T>(path, {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
    });
}

export async function login(email: string, password: string): Promise<User> {
    const response = await jsonRequest<{ user: User }>('/api/v1/auth/login', 'POST', {
        email,
        password,
    });
    return response.user;
}

export function logout(): Promise<void> {
    return request<void>('/api/v1/auth/logout', { method: 'POST' });
}

export function getMe(): Promise<User> {
    return request<User>('/api/v1/auth/me');
}

export function getProjects(): Promise<ProjectListItem[]> {
    return request<ProjectListItem[]>('/api/v1/projects');
}

export function getProject(projectId: string): Promise<ProjectDetail> {
    return request<ProjectDetail>(`/api/v1/projects/${projectId}`);
}

export function createProject(input: ProjectInput): Promise<ProjectDetail> {
    return jsonRequest<ProjectDetail>('/api/v1/projects', 'POST', input);
}

export function updateProject(projectId: string, input: ProjectInput): Promise<ProjectDetail> {
    return jsonRequest<ProjectDetail>(`/api/v1/projects/${projectId}`, 'PATCH', input);
}

export function createMilestone(projectId: string, input: MilestoneInput): Promise<Milestone> {
    return jsonRequest<Milestone>(`/api/v1/projects/${projectId}/milestones`, 'POST', input);
}

export function createDeliverable(
    milestoneId: string,
    input: DeliverableInput,
): Promise<DeliverableDetail> {
    return jsonRequest<DeliverableDetail>(
        `/api/v1/milestones/${milestoneId}/deliverables`,
        'POST',
        input,
    );
}

export function updateDeliverable(
    deliverableId: string,
    input: DeliverableInput,
): Promise<DeliverableDetail> {
    return jsonRequest<DeliverableDetail>(`/api/v1/deliverables/${deliverableId}`, 'PATCH', input);
}

export function getDeliverable(deliverableId: string): Promise<DeliverableDetail> {
    return request<DeliverableDetail>(`/api/v1/deliverables/${deliverableId}`);
}

export function getSubmissions(deliverableId: string): Promise<Submission[]> {
    return request<Submission[]>(`/api/v1/deliverables/${deliverableId}/submissions`);
}

export function submitDeliverable(
    deliverableId: string,
    files: File[],
    linkUrl: string,
): Promise<Submission> {
    const data = new FormData();
    for (const file of files) {
        data.append('files', file);
    }
    if (linkUrl.trim()) {
        data.append('link_url', linkUrl.trim());
    }

    return request<Submission>(`/api/v1/deliverables/${deliverableId}/submissions`, {
        method: 'POST',
        body: data,
    });
}

export function reviewDeliverable(
    deliverableId: string,
    decision: ReviewDecision,
): Promise<Review> {
    return jsonRequest<Review>(`/api/v1/deliverables/${deliverableId}/reviews`, 'POST', {
        decision,
    });
}

export function postMessage(deliverableId: string, body: string): Promise<ForumMessage> {
    return jsonRequest<ForumMessage>(`/api/v1/deliverables/${deliverableId}/messages`, 'POST', {
        body,
    });
}

export function getPendingReviews(): Promise<PendingReview[]> {
    return request<PendingReview[]>('/api/v1/reviews/pending');
}

export function fileDownloadUrl(fileId: string): string {
    return `/api/v1/files/${encodeURIComponent(fileId)}/download`;
}
