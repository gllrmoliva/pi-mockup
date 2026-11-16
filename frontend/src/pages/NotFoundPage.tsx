import { Link } from 'react-router-dom';

export function NotFoundPage() {
    return (
        <section className="panel not-found" aria-labelledby="not-found-title">
            <h1 id="not-found-title">Página no encontrada</h1>
            <p className="muted">
                La dirección que abriste no corresponde a una sección disponible de Hito.
            </p>
            <Link className="button" to="/">
                Volver a proyectos
            </Link>
        </section>
    );
}
