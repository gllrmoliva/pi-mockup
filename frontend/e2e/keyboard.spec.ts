import { expect, test } from '@playwright/test';

import {
    PROFESSOR,
    createProjectWithDeliverableViaApi,
    login,
    uniqueLabel,
} from './helpers';

test.describe('teclado y foco', () => {
    test('orden de tabulación del login', async ({ page }) => {
        await page.goto('/login');
        await expect(page.getByRole('heading', { name: 'Inicia sesión' })).toBeVisible();

        await page.keyboard.press('Tab');
        await expect(page.getByLabel('Correo institucional')).toBeFocused();

        await page.keyboard.press('Tab');
        await expect(page.getByLabel('Contraseña')).toBeFocused();

        await page.keyboard.press('Tab');
        await expect(page.getByRole('button', { name: 'Ingresar' })).toBeFocused();
    });

    test('skip link y cierre de diálogo con Escape', async ({ page, request }) => {
        const { project } = await createProjectWithDeliverableViaApi(request, {
            topic: uniqueLabel('Teclado'),
            title: uniqueLabel('Entregable teclado'),
        });

        await login(page, PROFESSOR);
        await page.keyboard.press('Tab');
        await expect(page.getByRole('link', { name: 'Saltar al contenido' })).toBeFocused();

        await page.goto(`/projects/${project.id}`);
        const trigger = page.getByRole('button', { name: 'Nuevo hito', exact: true });
        await trigger.click();

        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(dialog).toBeHidden();
        await expect(trigger).toBeFocused();
    });
});
