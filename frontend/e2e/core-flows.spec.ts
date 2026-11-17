import { expect, test } from '@playwright/test';

import {
    OTHER_PROFESSOR,
    OTHER_STUDENT,
    PROFESSOR,
    createProjectViaApi,
    createProjectWithDeliverableViaApi,
    createSubmittedDeliverableViaApi,
    uniqueLabel,
} from './helpers';
import {
    openHistoryThroughUi,
    pendingReviewVisible,
    reviewThroughUi,
    studentSeesProject,
    submitLinkThroughUi,
    createProjectThroughUi,
    expectProjectAccessDenied,
} from './flows';

test.describe('flujos de aceptación', () => {
    test('PA-1: el profesor crea un proyecto y el estudiante lo ve', async ({ page }) => {
        const topic = uniqueLabel('PA-1');
        const created = await createProjectThroughUi(page, {
            topic,
            deliverableTitle: uniqueLabel('Entregable PA-1'),
        });

        await studentSeesProject(page, {
            topic,
            deliverableTitle: created.deliverableTitle,
        });
    });

    test('PA-2: ciclo de revisión con dos versiones e historial', async ({
        page,
        request,
    }) => {
        const topic = uniqueLabel('PA-2');
        const title = uniqueLabel('Entregable PA-2');
        const { deliverable } = await createProjectWithDeliverableViaApi(request, {
            topic,
            title,
        });

        await submitLinkThroughUi(page, {
            deliverableId: deliverable.id,
            title,
            linkUrl: 'https://example.com/pa2/v1',
        });
        await reviewThroughUi(page, {
            deliverableId: deliverable.id,
            decision: 'changes_requested',
            message: 'Falta profundizar en los resultados.',
        });
        await submitLinkThroughUi(page, {
            deliverableId: deliverable.id,
            title,
            linkUrl: 'https://example.com/pa2/v2',
        });
        await reviewThroughUi(page, {
            deliverableId: deliverable.id,
            decision: 'approved',
        });

        await openHistoryThroughUi(page);
        await expect(page.getByRole('heading', { name: 'Versión 1' })).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Versión 2' })).toBeVisible();
    });

    test('PA-4: un estudiante no puede abrir un proyecto ajeno', async ({
        page,
        request,
    }) => {
        const project = await createProjectViaApi(request, {
            topic: uniqueLabel('PA-4'),
            managerEmail: OTHER_PROFESSOR,
            collaboratorEmail: OTHER_STUDENT,
        });

        await expectProjectAccessDenied(page, project.id);
    });

    test('PA-5: el profesor identifica una entrega pendiente', async ({
        page,
        request,
    }) => {
        const title = uniqueLabel('Entregable PA-5');
        const { deliverable } = await createSubmittedDeliverableViaApi(request, {
            topic: uniqueLabel('PA-5'),
            title,
            managerEmail: PROFESSOR,
        });

        const started = Date.now();
        await pendingReviewVisible(page, deliverable.title);
        expect(Date.now() - started).toBeLessThan(30_000);
    });
});
