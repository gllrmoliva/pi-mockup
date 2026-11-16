import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { professorUser, sampleProjectListItem } from '../test/fixtures';
import { jsonResponse, renderApp, stubFetch } from '../test/helpers';

describe('ProjectsPage', () => {
    it('muestra el portafolio y la bandeja de revisión del gestor', async () => {
        stubFetch((url) => {
            if (url === '/api/v1/auth/me') {
                return jsonResponse(professorUser);
            }
            if (url === '/api/v1/projects') {
                return jsonResponse([sampleProjectListItem]);
            }
            if (url === '/api/v1/reviews/pending') {
                return jsonResponse([
                    {
                        deliverable_id: 'd3',
                        title: 'Informe de avance 1',
                        project_id: 'p1',
                        project_topic: 'Reconocimiento de gestos para interfaces sin contacto',
                        milestone_name: 'Desarrollo y validación',
                        collaborator_name: 'Javiera Contreras',
                        version: 1,
                        submitted_at: '2026-11-15T21:14:00Z',
                    },
                ]);
            }
            return jsonResponse({}, 404);
        });

        renderApp('/');

        expect(await screen.findByRole('heading', { name: 'Hola, Camila' })).toBeInTheDocument();
        expect(await screen.findByText('Tienes 1 entrega por revisar.')).toBeInTheDocument();
        expect(
            await screen.findByRole('link', {
                name: 'Reconocimiento de gestos para interfaces sin contacto',
            }),
        ).toHaveAttribute('href', '/projects/p1');
        expect(await screen.findByText('1 de 2 entregables aprobados')).toBeInTheDocument();
        expect(await screen.findByRole('link', { name: 'Revisar' })).toHaveAttribute(
            'href',
            '/deliverables/d3',
        );
        expect(screen.getByRole('link', { name: 'Nuevo proyecto' })).toHaveAttribute(
            'href',
            '/projects/new',
        );
    });
});
