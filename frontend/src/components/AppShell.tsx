import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { useLogout, useMe } from '../api/queries';
import { initials } from '../utils/format';

export function AppShell() {
    const me = useMe();
    const logout = useLogout();
    const navigate = useNavigate();
    const user = me.data;

    if (!user) {
        return null;
    }

    function handleLogout() {
        logout.mutate(undefined, {
            onSuccess: () => {
                navigate('/login', { replace: true });
            },
        });
    }

    return (
        <>
            <a className="skip-link" href="#contenido">
                Saltar al contenido
            </a>
            <header className="site-header">
                <div className="site-header__inner">
                    <NavLink className="brand" to="/">
                        <span className="brand__name">Hito</span>
                        <span className="brand__tagline">Gestión de memorias y tesis</span>
                    </NavLink>

                    <nav className="site-nav" aria-label="Navegación principal">
                        <NavLink to="/" end>
                            Proyectos
                        </NavLink>
                    </nav>

                    <details className="account">
                        <summary className="account__trigger">
                            <span className="avatar" aria-hidden="true">
                                {initials(user.name)}
                            </span>
                            <span className="account__name">{user.name}</span>
                            <span className="account__chevron" aria-hidden="true">
                                ▾
                            </span>
                        </summary>
                        <div className="account__menu">
                            <p className="account__role">
                                {user.user_type === 'professor' ? 'Profesor' : 'Estudiante'}
                            </p>
                            <button
                                className="account__option"
                                type="button"
                                onClick={handleLogout}
                                disabled={logout.isPending}
                            >
                                {logout.isPending ? 'Cerrando sesión…' : 'Cerrar sesión'}
                            </button>
                        </div>
                    </details>
                </div>
            </header>
            <main id="contenido" className="page">
                <Outlet />
            </main>
        </>
    );
}
