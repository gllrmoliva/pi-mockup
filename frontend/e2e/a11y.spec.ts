import { expect, test } from '@playwright/test';

import {
    PROFESSOR,
    createSubmittedDeliverableViaApi,
    expectNoA11yViolations,
    login,
    uniqueLabel,
} from './helpers';

test.describe('accesibilidad WCAG 2.1 AA', () => {
    test.beforeEach(({ browserName }) => {
        test.skip(
            browserName !== 'chromium',
            'Las auditorías axe corren en Chromium; el smoke cubre el resto de motores.',
        );
    });

    test('pantalla de login', async ({ page }) => {
        await page.goto('/login');
        await expect(page.getByRole('heading', { name: 'Inicia sesión' })).toBeVisible();

        await expectNoA11yViolations(page);
    });

    test('portafolio y formulario de proyecto', async ({ page }) => {
        await login(page, PROFESSOR);
        await expectNoA11yViolations(page);

        await page.goto('/projects/new');
        await expect(page.getByRole('heading', { name: 'Nuevo proyecto' })).toBeVisible();
        await expectNoA11yViolations(page);
    });

    test('detalle y edición de proyecto', async ({ page, request }) => {
        const topic = uniqueLabel('A11Y proyecto');
        const { project } = await createSubmittedDeliverableViaApi(request, {
            topic,
            title: uniqueLabel('Entregable A11Y proyecto'),
        });

        await login(page, PROFESSOR);
        await page.goto(`/projects/${project.id}`);
        await expect(page.getByRole('heading', { name: topic })).toBeVisible();
        await expectNoA11yViolations(page);

        await page.goto(`/projects/${project.id}/edit`);
        await expect(page.getByRole('heading', { name: 'Editar proyecto' })).toBeVisible();
        await expectNoA11yViolations(page);
    });

    test('entregable e historial', async ({ page, request }) => {
        const title = uniqueLabel('Entregable A11Y detalle');
        const { deliverable } = await createSubmittedDeliverableViaApi(request, {
            topic: uniqueLabel('A11Y entregable'),
            title,
        });

        await login(page, PROFESSOR);
        await page.goto(`/deliverables/${deliverable.id}`);
        await expect(page.getByRole('heading', { name: title })).toBeVisible();
        await expectNoA11yViolations(page);

        await page.goto(`/deliverables/${deliverable.id}/history`);
        await expect(
            page.getByRole('heading', { name: 'Historial de versiones' }),
        ).toBeVisible();
        await expectNoA11yViolations(page);
    });

    test('página no encontrada', async ({ page, browserName }) => {
        test.skip(
            browserName !== 'chromium',
            'Axe sobre 404 se verifica en Chromium; el smoke cubre el resto de motores.',
        );
        await login(page, PROFESSOR);
        await page.goto('/ruta-inexistente');
        await expect(page.getByRole('heading', { name: 'Página no encontrada' })).toBeVisible();
        await expectNoA11yViolations(page);
    });
});
