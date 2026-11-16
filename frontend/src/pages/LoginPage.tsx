import { useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { ApiError } from '../api/client';
import { useLogin, useMe } from '../api/queries';
import { LoadingState } from '../components/LoadingState';

export function LoginPage() {
    const me = useMe();
    const login = useLogin();
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);

    if (me.isPending) {
        return <LoadingState label="Comprobando sesión…" />;
    }

    if (me.data) {
        return <Navigate to="/" replace />;
    }

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);

        if (!email.trim() || !password) {
            setError('Correo y/o contraseña vacíos.');
            return;
        }

        login.mutate(
            { email: email.trim(), password },
            {
                onSuccess: () => {
                    navigate('/', { replace: true });
                },
                onError: (loginError) => {
                    setError(
                        loginError instanceof ApiError
                            ? loginError.message
                            : 'No se pudo iniciar sesión.',
                    );
                },
            },
        );
    }

    return (
        <main className="auth-page">
            <section className="auth-card" aria-labelledby="login-title">
                <p className="auth-brand">
                    <span className="brand__name">Hito</span>
                    <span className="brand__tagline">Gestión de memorias y tesis</span>
                </p>

                <h1 id="login-title">Inicia sesión</h1>
                <p className="lead">
                    Entra con tu correo institucional para ver tus proyectos, entregas y revisiones.
                </p>

                {error ? (
                    <div className="alert" role="alert">
                        {error}
                    </div>
                ) : null}

                <form className="form" onSubmit={handleSubmit} noValidate>
                    <div className="field">
                        <label htmlFor="login-email">Correo institucional</label>
                        <input
                            id="login-email"
                            className="input"
                            type="email"
                            autoComplete="email"
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                            required
                        />
                    </div>
                    <div className="field">
                        <label htmlFor="login-password">Contraseña</label>
                        <input
                            id="login-password"
                            className="input"
                            type="password"
                            autoComplete="current-password"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}
                            required
                        />
                    </div>
                    <button
                        className="button button--block"
                        type="submit"
                        disabled={login.isPending}
                    >
                        {login.isPending ? 'Ingresando…' : 'Ingresar'}
                    </button>
                </form>

                <p className="login-note">Las cuentas son creadas por el equipo operador.</p>
            </section>
        </main>
    );
}
