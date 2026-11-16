import type { DeliverableDetail, ProjectDetail, ProjectListItem, User } from '../api/types';

export const professorUser: User = {
    id: 'u-professor',
    name: 'Camila Soto',
    email: 'camila.soto@udec.cl',
    user_type: 'professor',
    state: 'active',
};

export const studentUser: User = {
    id: 'u-student',
    name: 'Javiera Contreras',
    email: 'javiera.contreras@udec.cl',
    user_type: 'student',
    state: 'active',
};

export const sampleProjectListItem: ProjectListItem = {
    id: 'p1',
    topic: 'Reconocimiento de gestos para interfaces sin contacto',
    project_type: 'memoir',
    status: 'active',
    started_on: '2026-08-03',
    last_modified_at: '2026-11-16T12:00:00Z',
    my_role: 'manager',
    participants: [
        {
            id: 'u-professor',
            name: 'Camila Soto',
            email: 'camila.soto@udec.cl',
            role: 'manager',
        },
        {
            id: 'u-student',
            name: 'Javiera Contreras',
            email: 'javiera.contreras@udec.cl',
            role: 'collaborator',
        },
    ],
    total_deliverables: 2,
    approved_deliverables: 1,
    overdue_deliverables: 1,
    pending_review_deliverables: 1,
    next_deadline_at: '2026-11-20T23:59:00-03:00',
};

export const sampleProjectDetail: ProjectDetail = {
    id: 'p1',
    topic: 'Reconocimiento de gestos para interfaces sin contacto',
    project_type: 'memoir',
    status: 'active',
    started_on: '2026-08-03',
    last_modified_at: '2026-11-16T12:00:00Z',
    my_role: 'manager',
    participants: [
        {
            id: 'u-professor',
            name: 'Camila Soto',
            email: 'camila.soto@udec.cl',
            role: 'manager',
        },
        {
            id: 'u-student',
            name: 'Javiera Contreras',
            email: 'javiera.contreras@udec.cl',
            role: 'collaborator',
        },
    ],
    milestones: [
        {
            id: 'm1',
            name: 'Propuesta de memoria',
            order_index: 1,
            deliverables: [
                {
                    id: 'd1',
                    title: 'Anteproyecto',
                    deadline_at: '2026-09-04T23:59:00-03:00',
                    status: 'approved',
                    is_overdue: false,
                    latest_submission: {
                        version: 2,
                        submitted_at: '2026-08-28T18:30:00Z',
                        author_name: 'Javiera Contreras',
                    },
                    review: {
                        decision: 'approved',
                        reviewer_name: 'Camila Soto',
                        reviewed_at: '2026-08-30T12:00:00Z',
                    },
                },
            ],
        },
        {
            id: 'm2',
            name: 'Desarrollo y validación',
            order_index: 2,
            deliverables: [
                {
                    id: 'd3',
                    title: 'Informe de avance 1',
                    deadline_at: '2026-11-20T23:59:00-03:00',
                    status: 'submitted',
                    is_overdue: false,
                    latest_submission: {
                        version: 1,
                        submitted_at: '2026-11-15T21:14:00Z',
                        author_name: 'Javiera Contreras',
                    },
                    review: null,
                },
                {
                    id: 'd4',
                    title: 'Prototipo funcional',
                    deadline_at: '2026-10-12T23:59:00-03:00',
                    status: 'pending',
                    is_overdue: true,
                    latest_submission: null,
                    review: null,
                },
            ],
        },
    ],
};

export const sampleSubmission = {
    id: 's1',
    version: 1,
    submitted_at: '2026-11-15T21:14:00Z',
    link_url: null,
    author_id: 'u-student',
    author_name: 'Javiera Contreras',
    files: [
        {
            id: 'f1',
            original_name: 'informe-avance-1.pdf',
            mime_type: 'application/pdf',
            size_bytes: 3_400_000,
            sha256: 'a'.repeat(64),
        },
    ],
    review: null,
} satisfies DeliverableDetail['latest_submission'];

export const sampleManagerDeliverable: DeliverableDetail = {
    id: 'd3',
    project_id: 'p1',
    project_topic: 'Reconocimiento de gestos para interfaces sin contacto',
    milestone_id: 'm2',
    milestone_name: 'Desarrollo y validación',
    title: 'Informe de avance 1',
    description: 'Informe con el estado del trabajo y los primeros resultados.',
    deadline_at: '2026-11-20T23:59:00-03:00',
    allowed_formats: ['pdf', 'zip'],
    max_file_size_mb: 50,
    status: 'submitted',
    is_overdue: false,
    version_count: 1,
    my_role: 'manager',
    latest_submission: sampleSubmission,
    review: null,
    messages: [
        {
            id: 'msg1',
            body: 'Subí la primera versión del informe.',
            author_id: 'u-student',
            author_name: 'Javiera Contreras',
            created_at: '2026-11-15T21:16:00Z',
        },
    ],
};

export const sampleCollaboratorDeliverable: DeliverableDetail = {
    ...sampleManagerDeliverable,
    my_role: 'collaborator',
};
