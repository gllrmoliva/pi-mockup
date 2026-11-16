import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { professorUser } from '../test/fixtures';
import { jsonResponse, renderApp, stubFetch } from '../test/helpers';

const unauthorized = {
    error: {
        code: 'UNAUTHORIZED',
        message: 'No has iniciado sesión.',
    },
};

describe('LoginPage', () => {
    it('muestra el mensaje local cuando el formulario está vacío', async () => {
        stubFetch((url) => {
            if (url === '/api/v1/auth/me') {
                return jsonResponse(unauthorized, 401);
            }
            return jsonResponse({}, 404);
        });

        renderApp('/login');

        expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument();

        await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }));

        expect(await screen.findByRole('alert')).toHaveTextContent('Correo y/o contraseña vacíos.');
    });

    it('inicia sesión y muestra el portafolio', async () => {
        let loggedIn = false;
        const fetchMock = stubFetch((url, init) => {
            if (url === '/api/v1/auth/me') {
                return loggedIn ? jsonResponse(professorUser) : jsonResponse(unauthorized, 401);
            }
            if (url === '/api/v1/auth/login') {
                expect(init?.method).toBe('POST');
                loggedIn = true;
                return jsonResponse({ user: professorUser });
            }
            if (url === '/api/v1/projects') {
                return jsonResponse([]);
            }
            if (url === '/api/v1/reviews/pending') {
                return jsonResponse([]);
            }
            return jsonResponse({}, 404);
        });

        renderApp('/login');

        await screen.findByRole('heading', { name: 'Inicia sesión' });
        await userEvent.type(screen.getByLabelText('Correo institucional'), professorUser.email);
        await userEvent.type(screen.getByLabelText('Contraseña'), 'HitoDemo123!');
        await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }));

        expect(await screen.findByRole('heading', { name: 'Hola, Camila' })).toBeInTheDocument();
        expect(fetchMock).toHaveBeenCalledWith(
            '/api/v1/auth/login',
            expect.objectContaining({
                method: 'POST',
                credentials: 'include',
            }),
        );
    });
});
