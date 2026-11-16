import { Link, useParams } from 'react-router-dom';

import { useDeliverable, useSubmissionHistory } from '../api/queries';
import type { Submission } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { ReviewBlock } from '../components/ReviewBlock';
import { SubmissionFiles } from '../components/SubmissionFiles';
import { formatDateTime } from '../utils/format';

export function SubmissionHistoryPage() {
    const { deliverableId } = useParams<{ deliverableId: string }>();
    const deliverable = useDeliverable(deliverableId);
    const history = useSubmissionHistory(
        deliverable.data?.my_role === 'manager' ? deliverableId : undefined,
    );

    if (!deliverableId) {
        return <ErrorState message="No se pudo identificar el entregable." />;
    }

    if (deliverable.isPending) {
        return <LoadingState label="Cargando entregable…" />;
    }

    if (deliverable.isError || !deliverable.data) {
        return (
            <div className="stack">
                <Link className="back-link" to="/">
                    ← Proyectos
                </Link>
                <ErrorState message="No se pudo cargar el entregable." />
            </div>
        );
    }

    if (deliverable.data.my_role !== 'manager') {
        return (
            <div className="stack">
                <Link className="back-link" to={`/deliverables/${deliverableId}`}>
                    ← Volver al entregable
                </Link>
                <section className="panel" aria-labelledby="forbidden-title">
                    <h1 id="forbidden-title">Historial de versiones</h1>
                    <p className="muted">No tienes acceso al historial de versiones.</p>
                </section>
            </div>
        );
    }

    if (history.isPending) {
        return <LoadingState label="Cargando historial…" />;
    }

    if (history.isError || !history.data) {
        return (
            <div className="stack">
                <Link className="back-link" to={`/deliverables/${deliverableId}`}>
                    ← Volver al entregable
                </Link>
                <ErrorState message="No se pudo cargar el historial de versiones." />
            </div>
        );
    }

    return (
        <div className="stack">
            <Link className="back-link" to={`/deliverables/${deliverableId}`}>
                ← Volver al entregable
            </Link>

            <div className="page-header">
                <div>
                    <h1>Historial de versiones</h1>
                    <p className="lead">
                        {deliverable.data.title} · Hito «{deliverable.data.milestone_name}»
                    </p>
                </div>
            </div>

            <p className="panel-note">
                Cada entrega genera una versión nueva: ninguna se edita ni se borra.
            </p>

            {history.data.length === 0 ? (
                <EmptyState title="Este entregable aún no tiene versiones.">
                    <p className="muted">Las entregas aparecerán aquí en orden de versión.</p>
                </EmptyState>
            ) : (
                <ol className="history-list">
                    {history.data.map((submission) => (
                        <HistoryItem key={submission.id} submission={submission} />
                    ))}
                </ol>
            )}
        </div>
    );
}

function HistoryItem({ submission }: { submission: Submission }) {
    return (
        <li className="panel history-card">
            <div className="section-heading">
                <h2>Versión {submission.version}</h2>
                <span className="chip chip--neutral">
                    {submission.files.length} archivo
                    {submission.files.length === 1 ? '' : 's'}
                </span>
            </div>

            <p className="muted small">
                Entregada por {submission.author_name} el {formatDateTime(submission.submitted_at)}.
            </p>

            <SubmissionFiles files={submission.files} />

            {submission.link_url ? (
                <p className="link-line">
                    Enlace de la entrega:{' '}
                    <a href={submission.link_url} target="_blank" rel="noreferrer">
                        {submission.link_url}
                    </a>
                </p>
            ) : null}

            <div className="history-card__review">
                {submission.review ? (
                    <ReviewBlock review={submission.review} />
                ) : (
                    <p className="muted small">Sin revisión registrada.</p>
                )}
            </div>
        </li>
    );
}
