import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import {
    professorUser,
    sampleCollaboratorDeliverable,
    sampleManagerDeliverable,
    sampleSubmission,
    studentUser,
} from '../test/fixtures';
import { jsonResponse, renderApp, stubFetch } from '../test/helpers';

describe('DeliverablePage', () => {
    it('permite al gestor revisar la última entrega', async () => {
        let reviewed = false;
        stubFetch((url, init) => {
            if (url === '/api/v1/auth/me') {
                return jsonResponse(professorUser);
            }
            if (url === '/api/v1/deliverables/d3' && init?.method !== 'POST') {
                return jsonResponse(
                    reviewed
                        ? {
                              ...sampleManagerDeliverable,
                              status: 'approved',
                              review: {
                                  id: 'r1',
                                  decision: 'approved',
                                  reviewer_name: 'Camila Soto',
                                  reviewed_at: '2026-11-16T12:30:00Z',
                              },
                              latest_submission: {
                                  ...sampleSubmission,
                                  review: {
                                      id: 'r1',
                                      decision: 'approved',
                                      reviewer_name: 'Camila Soto',
                                      reviewed_at: '2026-11-16T12:30:00Z',
                                  },
                              },
                          }
                        : sampleManagerDeliverable,
                );
            }
            if (url === '/api/v1/deliverables/d3/reviews' && init?.method === 'POST') {
                reviewed = true;
                return jsonResponse(
                    {
                        id: 'r1',
                        decision: 'approved',
                        reviewer_name: 'Camila Soto',
                        reviewed_at: '2026-11-16T12:30:00Z',
                    },
                    201,
                );
            }
            return jsonResponse({}, 404);
        });

        renderApp('/deliverables/d3');

        expect(
            await screen.findByRole('heading', {
                name: 'Informe de avance 1',
            }),
        ).toBeInTheDocument();
        expect(screen.getByText('Tu revisión')).toBeInTheDocument();
        expect(
            screen.getByRole('link', {
                name: 'Ver historial de versiones (1)',
            }),
        ).toHaveAttribute('href', '/deliverables/d3/history');
        expect(
            screen.queryByRole('heading', {
                name: 'Entregar una nueva versión',
            }),
        ).not.toBeInTheDocument();

        await userEvent.click(screen.getByRole('radio', { name: /Aprobar la entrega/ }));
        await userEvent.click(screen.getByRole('button', { name: 'Registrar revisión' }));

        expect(
            await screen.findByText('Revisión registrada. Puedes dejar un comentario en el foro.'),
        ).toBeInTheDocument();
    });

    it('valida archivos y mensajes vacíos del colaborador', async () => {
        stubFetch((url) => {
            if (url === '/api/v1/auth/me') {
                return jsonResponse(studentUser);
            }
            if (url === '/api/v1/deliverables/d3') {
                return jsonResponse(sampleCollaboratorDeliverable);
            }
            return jsonResponse({}, 404);
        });

        renderApp('/deliverables/d3');

        expect(
            await screen.findByRole('heading', {
                name: 'Entregar una nueva versión',
            }),
        ).toBeInTheDocument();
        expect(
            screen.getByText(
                'Solo ves la última versión entregada. Las anteriores se conservan y el equipo gestor puede verlas en el historial.',
            ),
        ).toBeInTheDocument();
        expect(screen.queryByRole('heading', { name: 'Tu revisión' })).not.toBeInTheDocument();

        await userEvent.click(screen.getByRole('button', { name: 'Enviar entrega' }));
        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Adjunta al menos un archivo válido: PDF, ZIP.',
        );

        await userEvent.click(screen.getByRole('button', { name: 'Publicar mensaje' }));
        expect(screen.getByText('El comentario no puede estar vacío.')).toBeInTheDocument();
    });
});
