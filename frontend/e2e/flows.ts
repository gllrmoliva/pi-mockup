import { expect, type Page } from '@playwright/test';

import {
    PROFESSOR,
    STUDENT,
    expectNoHorizontalScroll,
    futureDateTimeLocal,
    login,
} from './helpers';

export type CreatedProject = {
    topic: string;
    projectId: string;
    deliverableTitle: string;
};

export async function createProjectThroughUi(
    page: Page,
    options: {
        topic: string;
        collaboratorEmail?: string;
        deliverableTitle?: string;
    },
): Promise<CreatedProject> {
    const {
        topic,
        collaboratorEmail = STUDENT,
        deliverableTitle = 'Entregable E2E',
    } = options;

    await login(page, PROFESSOR);
    await page.getByRole('link', { name: 'Nuevo proyecto', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Nuevo proyecto' })).toBeVisible();

    await page.getByLabel('Tema del proyecto').fill(topic);
    await page.getByLabel('Correo del colaborador').fill(collaboratorEmail);
    await page.getByRole('button', { name: 'Agregar colaborador' }).click();
    await page.getByRole('button', { name: 'Crear proyecto' }).click();

    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
    await expect(page.getByRole('heading', { name: topic })).toBeVisible();
    const projectId = page.url().split('/projects/')[1];
    if (!projectId) {
        throw new Error('No se pudo obtener el id del proyecto creado.');
    }

    await createMilestoneThroughUi(page, 'Hito 1');
    await createMilestoneThroughUi(page, 'Hito 2');
    await createDeliverableThroughUi(page, 'Hito 1', deliverableTitle);

    return { topic, projectId, deliverableTitle };
}

export async function createMilestoneThroughUi(page: Page, name: string): Promise<void> {
    await page.getByRole('button', { name: 'Nuevo hito', exact: true }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByRole('heading', { name: 'Nuevo hito' })).toBeVisible();
    await expectNoHorizontalScroll(page);
    await dialog.getByLabel('Nombre del hito').fill(name);
    await dialog.getByRole('button', { name: 'Crear hito' }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
}

export async function createDeliverableThroughUi(
    page: Page,
    milestoneName: string,
    title: string,
): Promise<void> {
    const milestone = page.locator('li.milestone').filter({ hasText: milestoneName });
    await milestone.getByRole('button', { name: 'Nuevo entregable' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByRole('heading', { name: 'Nuevo entregable' })).toBeVisible();
    await expectNoHorizontalScroll(page);
    await dialog.getByLabel('Nombre del entregable').fill(title);
    await dialog.getByLabel('Descripción').fill(`Descripción de ${title}`);
    await dialog.getByLabel('Fecha y hora límite').fill(futureDateTimeLocal(7));
    await dialog.getByRole('button', { name: 'Crear entregable' }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByRole('link', { name: title, exact: true })).toBeVisible();
}

export async function studentSeesProject(
    page: Page,
    options: {
        topic: string;
        milestoneName?: string;
        deliverableTitle?: string;
    },
): Promise<void> {
    const {
        topic,
        milestoneName = 'Hito 1',
        deliverableTitle = 'Entregable E2E',
    } = options;
    await login(page, STUDENT);
    await page.getByRole('link', { name: topic, exact: true }).click();
    await expect(page.getByRole('heading', { name: topic })).toBeVisible();
    await expect(page.getByRole('heading', { name: milestoneName, exact: true })).toBeVisible();
    await expect(
        page.getByRole('link', { name: deliverableTitle, exact: true }),
    ).toBeVisible();
}

export async function submitLinkThroughUi(
    page: Page,
    options: {
        deliverableId: string;
        title: string;
        linkUrl: string;
    },
): Promise<void> {
    const { deliverableId, title, linkUrl } = options;
    await login(page, STUDENT);
    await page.goto(`/deliverables/${deliverableId}`);
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    await page.getByLabel('Enlace de la entrega').fill(linkUrl);
    await page.getByRole('button', { name: 'Enviar entrega' }).click();
    await expect(page.getByText(/Entrega enviada\. La versión \d+ ya está disponible\./)).toBeVisible();
    await expectDeliverableStatus(page, 'Entregado');
}

export async function reviewThroughUi(
    page: Page,
    options: {
        deliverableId: string;
        decision: 'approved' | 'changes_requested';
        message?: string;
    },
): Promise<void> {
    const { deliverableId, decision, message } = options;
    await login(page, PROFESSOR);
    await page.goto(`/deliverables/${deliverableId}`);

    const decisionName =
        decision === 'approved' ? /Aprobar la entrega/ : /Solicitar cambios/;
    await page.getByRole('radio', { name: decisionName }).check();
    if (message) {
        await page.getByLabel('Mensaje para el foro (opcional)').fill(message);
    }
    await page.getByRole('button', { name: 'Registrar revisión' }).click();

    if (message) {
        await expect(
            page.getByText('Revisión registrada y mensaje publicado en el foro.'),
        ).toBeVisible();
    } else {
        await expect(
            page.getByText('Revisión registrada. Puedes dejar un comentario en el foro.'),
        ).toBeVisible();
    }

    await expectDeliverableStatus(
        page,
        decision === 'approved' ? 'Aprobado' : 'Cambios solicitados',
    );
}

export async function expectDeliverableStatus(page: Page, status: string): Promise<void> {
    const panel = page.locator('section[aria-label="Estado del entregable"]');
    await expect(panel.getByText(status, { exact: true })).toBeVisible();
}

export async function openHistoryThroughUi(page: Page): Promise<void> {
    await page.getByRole('link', { name: /Ver historial de versiones/ }).click();
    await expect(page.getByRole('heading', { name: 'Historial de versiones' })).toBeVisible();
}

export async function pendingReviewVisible(page: Page, title: string): Promise<void> {
    await login(page, PROFESSOR);
    const section = page.locator('section[aria-labelledby="pending-title"]');
    await expect(section.getByRole('heading', { name: 'Esperan tu revisión' })).toBeVisible();
    await expect(section.getByRole('link', { name: title, exact: true })).toBeVisible();
}

export async function expectProjectAccessDenied(
    page: Page,
    projectId: string,
): Promise<void> {
    await login(page, STUDENT);
    await page.goto(`/projects/${projectId}`);
    await expect(
        page.getByRole('alert').getByText(
            'No se pudo cargar el proyecto. Puede que no exista o que no tengas acceso.',
        ),
    ).toBeVisible();
}
