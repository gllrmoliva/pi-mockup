import { expect, type APIRequestContext, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import type { DeliverableDetail, Milestone, ProjectDetail, Submission } from '../src/api/types';

export const PROFESSOR = 'camila.soto@udec.cl';
export const STUDENT = 'javiera.contreras@udec.cl';
export const OTHER_PROFESSOR = 'antonio.skorin@udec.cl';
export const OTHER_STUDENT = 'fernanda.torres@udec.cl';

const A11Y_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

export function demoPassword(): string {
    const password = process.env.E2E_DEMO_PASSWORD;
    if (!password) {
        throw new Error('E2E_DEMO_PASSWORD is required. Run scripts/nfr/e2e.sh.');
    }
    return password;
}

export function uniqueLabel(prefix: string): string {
    return `${prefix} ${Date.now()} ${Math.random().toString(36).slice(2, 8)}`;
}

export function futureDateTimeLocal(days = 7): string {
    const date = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
    const pad = (value: number): string => String(value).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
        date.getHours(),
    )}:${pad(date.getMinutes())}`;
}

export async function login(page: Page, email: string): Promise<void> {
    await page.context().clearCookies();
    await page.goto('/login');
    await page.getByLabel('Correo institucional').fill(email);
    await page.getByLabel('Contraseña').fill(demoPassword());
    await page.getByRole('button', { name: 'Ingresar' }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole('heading', { name: /^Hola, / })).toBeVisible();
}

export async function apiLogin(request: APIRequestContext, email: string): Promise<void> {
    const response = await request.post('/api/v1/auth/login', {
        data: { email, password: demoPassword() },
    });
    expect(response.status()).toBe(200);
}

export async function createProjectViaApi(
    request: APIRequestContext,
    options: {
        topic: string;
        managerEmail?: string;
        collaboratorEmail?: string;
    },
): Promise<ProjectDetail> {
    const {
        topic,
        managerEmail = PROFESSOR,
        collaboratorEmail = STUDENT,
    } = options;
    await apiLogin(request, managerEmail);
    const response = await request.post('/api/v1/projects', {
        data: {
            topic,
            project_type: 'memoir',
            manager_emails: [],
            collaborator_emails: [collaboratorEmail],
        },
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as ProjectDetail;
}

export async function createMilestoneViaApi(
    request: APIRequestContext,
    projectId: string,
    name: string,
    position = 1,
): Promise<Milestone> {
    const response = await request.post(`/api/v1/projects/${projectId}/milestones`, {
        data: { name, position },
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as Milestone;
}

export async function createDeliverableViaApi(
    request: APIRequestContext,
    milestoneId: string,
    title: string,
): Promise<DeliverableDetail> {
    const response = await request.post(`/api/v1/milestones/${milestoneId}/deliverables`, {
        data: {
            title,
            description: `Descripción de ${title}`,
            deadline_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
            allowed_formats: ['pdf', 'zip'],
            max_file_size_mb: 50,
        },
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as DeliverableDetail;
}

export async function submitViaApi(
    request: APIRequestContext,
    deliverableId: string,
    collaboratorEmail = STUDENT,
): Promise<Submission> {
    await apiLogin(request, collaboratorEmail);
    const response = await request.post(
        `/api/v1/deliverables/${deliverableId}/submissions`,
        {
            form: {
                link_url: `https://example.com/e2e/${deliverableId}`,
            },
        },
    );
    expect(response.status()).toBe(201);
    return (await response.json()) as Submission;
}

export async function createProjectWithDeliverableViaApi(
    request: APIRequestContext,
    options: {
        topic: string;
        title: string;
        managerEmail?: string;
        collaboratorEmail?: string;
    },
): Promise<{
    project: ProjectDetail;
    milestone: Milestone;
    deliverable: DeliverableDetail;
}> {
    const project = await createProjectViaApi(request, {
        topic: options.topic,
        managerEmail: options.managerEmail,
        collaboratorEmail: options.collaboratorEmail,
    });
    const milestone = await createMilestoneViaApi(request, project.id, 'Hito E2E');
    const deliverable = await createDeliverableViaApi(
        request,
        milestone.id,
        options.title,
    );
    return { project, milestone, deliverable };
}

export async function createSubmittedDeliverableViaApi(
    request: APIRequestContext,
    options: {
        topic: string;
        title: string;
        managerEmail?: string;
        collaboratorEmail?: string;
    },
): Promise<{
    project: ProjectDetail;
    milestone: Milestone;
    deliverable: DeliverableDetail;
}> {
    const data = await createProjectWithDeliverableViaApi(request, options);
    await submitViaApi(request, data.deliverable.id, options.collaboratorEmail);
    return data;
}

export async function expectNoHorizontalScroll(page: Page): Promise<void> {
    const metrics = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
    }));
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.innerWidth + 1);
}

export async function expectNoA11yViolations(page: Page): Promise<void> {
    const results = await new AxeBuilder({ page })
        .withTags(A11Y_TAGS)
        .analyze();
    expect(results.violations).toEqual([]);
}
