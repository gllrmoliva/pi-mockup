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
        expect(screen.getByText('Camila Soto ha creado el entregable.')).toBeInTheDocument();
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

    it('publica el mensaje opcional después de solicitar cambios', async () => {
        let reviewed = false;
        let reviewPayload: unknown;
        let messagePayload: unknown;
        const decision = {
            id: 'r2',
            decision: 'changes_requested',
            reviewer_name: 'Camila Soto',
            reviewed_at: '2026-11-16T12:30:00Z',
        };

        stubFetch((url, init) => {
            if (url === '/api/v1/auth/me') {
                return jsonResponse(professorUser);
            }
            if (url === '/api/v1/deliverables/d3' && init?.method !== 'POST') {
                return jsonResponse(
                    reviewed
                        ? {
                              ...sampleManagerDeliverable,
                              status: 'changes_requested',
                              review: decision,
                              latest_submission: {
                                  ...sampleSubmission,
                                  review: decision,
                              },
                          }
                        : sampleManagerDeliverable,
                );
            }
            if (url === '/api/v1/deliverables/d3/reviews' && init?.method === 'POST') {
                reviewed = true;
                reviewPayload = JSON.parse(String(init.body));
                return jsonResponse(decision, 201);
            }
            if (url === '/api/v1/deliverables/d3/messages' && init?.method === 'POST') {
                messagePayload = JSON.parse(String(init.body));
                return jsonResponse(
                    {
                        id: 'msg2',
                        kind: 'user',
                        body: 'Corrige la sección 2.',
                        author_id: 'u-professor',
                        author_name: 'Camila Soto',
                        created_at: '2026-11-16T12:31:00Z',
                    },
                    201,
                );
            }
            return jsonResponse({}, 404);
        });

        renderApp('/deliverables/d3');

        await screen.findByRole('heading', { name: 'Informe de avance 1' });
        expect(screen.getByLabelText('Mensaje para el foro (opcional)')).toBeInTheDocument();

        await userEvent.click(screen.getByRole('radio', { name: /Solicitar cambios/ }));
        await userEvent.type(
            screen.getByLabelText('Mensaje para el foro (opcional)'),
            'Corrige la sección 2.',
        );
        await userEvent.click(screen.getByRole('button', { name: 'Registrar revisión' }));

        expect(
            await screen.findByText('Revisión registrada y mensaje publicado en el foro.'),
        ).toBeInTheDocument();
        expect(reviewPayload).toEqual({ decision: 'changes_requested' });
        expect(messagePayload).toEqual({ body: 'Corrige la sección 2.' });
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
            'Adjunta al menos un archivo válido (PDF, ZIP) o ingresa un enlace HTTPS.',
        );

        await userEvent.click(screen.getByRole('button', { name: 'Publicar mensaje' }));
        expect(screen.getByText('El comentario no puede estar vacío.')).toBeInTheDocument();
    });

    it('permite entregar solo con un enlace HTTPS', async () => {
        stubFetch((url, init) => {
            if (url === '/api/v1/auth/me') {
                return jsonResponse(studentUser);
            }
            if (url === '/api/v1/deliverables/d3' && init?.method !== 'POST') {
                return jsonResponse(sampleCollaboratorDeliverable);
            }
            if (url === '/api/v1/deliverables/d3/submissions' && init?.method === 'POST') {
                const data = init.body as FormData;
                expect(data.get('link_url')).toBe('https://example.com/entrega-solo-enlace');
                expect(data.getAll('files')).toHaveLength(0);
                return jsonResponse(
                    {
                        ...sampleSubmission,
                        version: 2,
                        files: [],
                        link_url: 'https://example.com/entrega-solo-enlace',
                    },
                    201,
                );
            }
            return jsonResponse({}, 404);
        });

        renderApp('/deliverables/d3');

        await screen.findByRole('heading', {
            name: 'Entregar una nueva versión',
        });
        await userEvent.type(
            screen.getByLabelText('Enlace de la entrega'),
            'https://example.com/entrega-solo-enlace',
        );
        await userEvent.click(screen.getByRole('button', { name: 'Enviar entrega' }));

        expect(
            await screen.findByText('Entrega enviada. La versión 2 ya está disponible.'),
        ).toBeInTheDocument();
    });
});
