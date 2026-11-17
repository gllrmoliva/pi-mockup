import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import type { ProjectDetail, ProjectListItem } from '../src/api/types';
import { apiLogin, login } from './helpers';

const PERF_PROFESSOR = 'profe0001@perf.example.com';
const NAV_SAMPLES = 10;
const UPLOAD_SAMPLES = 3;
const UPLOAD_BYTES = 10 * 1024 * 1024;

type Timings = {
    samples: number;
    p50: number;
    p95: number;
    p99: number;
    max: number;
};

function percentile(values: number[], percent: number): number {
    if (values.length === 0) {
        return 0;
    }
    const sorted = [...values].sort((left, right) => left - right);
    const index = Math.min(
        sorted.length - 1,
        Math.max(0, Math.round((percent / 100) * (sorted.length - 1))),
    );
    return Math.round(sorted[index] ?? 0);
}

function timings(values: number[]): Timings {
    return {
        samples: values.length,
        p50: percentile(values, 50),
        p95: percentile(values, 95),
        p99: percentile(values, 99),
        max: Math.round(Math.max(...values, 0)),
    };
}

async function measure(action: () => Promise<void>): Promise<number> {
    const started = Date.now();
    await action();
    return Date.now() - started;
}

test.describe('RNF-R-1 tiempos de navegación y subida', () => {
    test.skip(process.env.E2E_PERF !== '1', 'Se ejecuta con E2E_PERF=1.');

    test('mide navegación y subida de 10 MB', async ({ page, request }) => {
        test.setTimeout(180_000);

        await apiLogin(request, PERF_PROFESSOR);
        const projectsResponse = await request.get('/api/v1/projects');
        expect(projectsResponse.status()).toBe(200);
        const projects = (await projectsResponse.json()) as ProjectListItem[];

        let project: ProjectDetail | undefined;
        for (const summary of projects.slice(0, 8)) {
            const detailResponse = await request.get(
                `/api/v1/projects/${summary.id}`,
            );
            if (detailResponse.status() !== 200) {
                continue;
            }
            const detail = (await detailResponse.json()) as ProjectDetail;
            if (detail.milestones.some((milestone) => milestone.deliverables.length > 0)) {
                project = detail;
                break;
            }
        }
        if (!project) {
            throw new Error('No hay un proyecto de rendimiento con entregables.');
        }

        const deliverables = project.milestones.flatMap(
            (milestone) => milestone.deliverables,
        );
        const openDeliverable = deliverables.find(
            (deliverable) => deliverable.status !== 'approved',
        );
        const navDeliverable = deliverables[0];
        if (!navDeliverable) {
            throw new Error('No hay entregables para medir navegación.');
        }
        const collaborator = project.participants.find(
            (participant) => participant.role === 'collaborator',
        );
        if (!collaborator) {
            throw new Error('No hay colaborador para medir la subida.');
        }

        await login(page, PERF_PROFESSOR);

        const portfolio: number[] = [];
        const projectPage: number[] = [];
        const deliverablePage: number[] = [];

        for (let sample = 0; sample < NAV_SAMPLES; sample += 1) {
            portfolio.push(
                await measure(async () => {
                    await page.goto('/');
                    await expect(page.getByRole('heading', { name: /^Hola, / })).toBeVisible();
                }),
            );
            projectPage.push(
                await measure(async () => {
                    await page.goto(`/projects/${project.id}`);
                    await expect(page.getByRole('heading', { name: project.topic })).toBeVisible();
                }),
            );
            deliverablePage.push(
                await measure(async () => {
                    await page.goto(`/deliverables/${navDeliverable.id}`);
                    await expect(
                        page.getByRole('heading', { name: navDeliverable.title }),
                    ).toBeVisible();
                }),
            );
        }

        if (!openDeliverable) {
            throw new Error('No hay un entregable abierto para medir la subida.');
        }

        await login(page, collaborator.email);
        await page.goto(`/deliverables/${openDeliverable.id}`);
        await expect(
            page.getByRole('heading', { name: openDeliverable.title }),
        ).toBeVisible();

        const upload: number[] = [];
        for (let sample = 0; sample < UPLOAD_SAMPLES; sample += 1) {
            const fileInput = page.locator('#deliverable-files');
            await fileInput.setInputFiles({
                name: `perf-${sample}.pdf`,
                mimeType: 'application/pdf',
                buffer: Buffer.alloc(UPLOAD_BYTES),
            });
            upload.push(
                await measure(async () => {
                    const responsePromise = page.waitForResponse(
                        (response) =>
                            response.url().includes(
                                `/deliverables/${openDeliverable.id}/submissions`,
                            ) && response.request().method() === 'POST',
                    );
                    await page.getByRole('button', { name: 'Enviar entrega' }).click();
                    await responsePromise;
                    await expect(page.getByText(/Entrega enviada\./)).toBeVisible();
                }),
            );
        }

        const report = {
            generated_at: new Date().toISOString(),
            base_url: process.env.E2E_BASE_URL ?? '',
            navigation: {
                portfolio: timings(portfolio),
                project: timings(projectPage),
                deliverable: timings(deliverablePage),
            },
            upload: timings(upload),
            targets: {
                navigation_p95_ms: 500,
                upload_p95_ms: 3000,
            },
        };
        const outputDir = join(process.cwd(), '..', 'reports', 'nfr');
        mkdirSync(outputDir, { recursive: true });
        writeFileSync(
            join(outputDir, 'navigation.json'),
            `${JSON.stringify(report, null, 2)}\n`,
            'utf8',
        );

        if (process.env.E2E_PERF_ENFORCE === '1') {
            expect(report.navigation.portfolio.p95).toBeLessThanOrEqual(500);
            expect(report.navigation.project.p95).toBeLessThanOrEqual(500);
            expect(report.navigation.deliverable.p95).toBeLessThanOrEqual(500);
            expect(report.upload.p95).toBeLessThanOrEqual(3000);
        }
    });
});
