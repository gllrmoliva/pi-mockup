import { expect, test } from '@playwright/test';

import { PROFESSOR, login } from './helpers';

test.describe('navegador soportado', () => {
    test('login, portafolio, proyecto y entregable', async ({ page }) => {
        await login(page, PROFESSOR);

        const projectLink = page
            .getByRole('link', { name: /Reconocimiento de gestos para interfaces/ })
            .first();
        await expect(projectLink).toBeVisible();
        await projectLink.click();

        await expect(
            page.getByRole('heading', {
                name: /Reconocimiento de gestos para interfaces/,
            }),
        ).toBeVisible();

        const deliverableLink = page.locator('.deliverable-row a').first();
        await expect(deliverableLink).toBeVisible();
        await deliverableLink.click();
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    });
});
