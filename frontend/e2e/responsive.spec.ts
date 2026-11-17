import { expect, test } from '@playwright/test';

import {
    PROFESSOR,
    createProjectWithDeliverableViaApi,
    createSubmittedDeliverableViaApi,
    expectNoHorizontalScroll,
    login,
    uniqueLabel,
} from './helpers';
import {
    createProjectThroughUi,
    openHistoryThroughUi,
    pendingReviewVisible,
    reviewThroughUi,
    studentSeesProject,
    submitLinkThroughUi,
} from './flows';

test.describe('diseño responsivo a 360 px', () => {
    test.use({ viewport: { width: 360, height: 800 } });

    test.beforeEach(({ browserName }) => {
        test.skip(browserName !== 'chromium', 'La verificación 360 px corre en Chromium.');
    });

    test('portafolio y formulario de proyecto', async ({ page }) => {
        await login(page, PROFESSOR);
        await expectNoHorizontalScroll(page);

        await page.getByRole('link', { name: 'Nuevo proyecto', exact: true }).click();
        await expect(page.getByRole('heading', { name: 'Nuevo proyecto' })).toBeVisible();
        await expectNoHorizontalScroll(page);
    });

    test('PA-1 a 360 px', async ({ page }) => {
        const topic = uniqueLabel('U2-PA-1');
        const created = await createProjectThroughUi(page, {
            topic,
            deliverableTitle: 'Entregable U2 PA-1',
        });
        await expectNoHorizontalScroll(page);

        await studentSeesProject(page, {
            topic,
            deliverableTitle: created.deliverableTitle,
        });
        await expectNoHorizontalScroll(page);
    });

    test('PA-2 a 360 px', async ({ page, request }) => {
        const title = uniqueLabel('Entregable U2 PA-2');
        const { deliverable } = await createProjectWithDeliverableViaApi(request, {
            topic: uniqueLabel('U2-PA-2'),
            title,
        });

        await submitLinkThroughUi(page, {
            deliverableId: deliverable.id,
            title,
            linkUrl: 'https://example.com/u2/v1',
        });
        await expectNoHorizontalScroll(page);

        await reviewThroughUi(page, {
            deliverableId: deliverable.id,
            decision: 'changes_requested',
            message: 'Ajusta la sección de resultados.',
        });
        await expectNoHorizontalScroll(page);

        await submitLinkThroughUi(page, {
            deliverableId: deliverable.id,
            title,
            linkUrl: 'https://example.com/u2/v2',
        });
        await expectNoHorizontalScroll(page);

        await reviewThroughUi(page, {
            deliverableId: deliverable.id,
            decision: 'approved',
        });
        await expectNoHorizontalScroll(page);

        await openHistoryThroughUi(page);
        await expectNoHorizontalScroll(page);
    });

    test('PA-5 a 360 px', async ({ page, request }) => {
        const title = uniqueLabel('Entregable U2 PA-5');
        const { deliverable } = await createSubmittedDeliverableViaApi(request, {
            topic: uniqueLabel('U2-PA-5'),
            title,
        });

        await pendingReviewVisible(page, deliverable.title);
        await expectNoHorizontalScroll(page);
    });
});
