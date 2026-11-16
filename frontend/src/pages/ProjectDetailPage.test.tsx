import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { professorUser, sampleProjectDetail } from '../test/fixtures';
import { jsonResponse, renderApp, stubFetch } from '../test/helpers';

function stubProjectDetail() {
    stubFetch((url) => {
        if (url === '/api/v1/auth/me') {
            return jsonResponse(professorUser);
        }
        if (url === '/api/v1/projects/p1') {
            return jsonResponse(sampleProjectDetail);
        }
        return jsonResponse({}, 404);
    });
}

describe('ProjectDetailPage', () => {
    it('muestra hitos, entregables y acciones del gestor', async () => {
        stubProjectDetail();

        renderApp('/projects/p1');

        expect(
            await screen.findByRole('heading', {
                name: 'Reconocimiento de gestos para interfaces sin contacto',
            }),
        ).toBeInTheDocument();
        expect(screen.getByText('Propuesta de memoria')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Informe de avance 1' })).toHaveAttribute(
            'href',
            '/deliverables/d3',
        );
        expect(screen.getByText('Atrasado')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Editar proyecto' })).toHaveAttribute(
            'href',
            '/projects/p1/edit',
        );
        expect(screen.getByRole('link', { name: 'Revisar' })).toHaveAttribute(
            'href',
            '/deliverables/d3',
        );
    });

    it('valida el nombre al crear un hito', async () => {
        stubProjectDetail();

        renderApp('/projects/p1');

        await screen.findByRole('heading', {
            name: 'Reconocimiento de gestos para interfaces sin contacto',
        });
        await userEvent.click(screen.getByRole('button', { name: 'Nuevo hito' }));

        expect(await screen.findByRole('heading', { name: 'Nuevo hito' })).toBeInTheDocument();
        await userEvent.click(screen.getByRole('button', { name: 'Crear hito' }));

        expect(await screen.findByRole('alert')).toHaveTextContent('El Hito debe tener un nombre.');
    });
});
