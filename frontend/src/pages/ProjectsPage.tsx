import { Link } from 'react-router-dom';

import { useMe, usePendingReviews, useProjects } from '../api/queries';
import type { PendingReview, ProjectListItem } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusChip } from '../components/StatusChip';
import { firstName, formatDateTime, projectTypeLabels } from '../utils/format';

function PendingReviewRow({ item }: { item: PendingReview }) {
    return (
        <li className="pending-row">
            <div className="pending-row__main">
                <Link to={`/deliverables/${item.deliverable_id}`}>{item.title}</Link>
                <p className="muted">
                    {item.collaborator_name} · {item.project_topic}
                </p>
            </div>
            <div className="pending-row__meta">
                <StatusChip status="submitted" />
                <span className="muted">
                    Versión {item.version} · {formatDateTime(item.submitted_at)}
                </span>
            </div>
            <Link className="button button--small" to={`/deliverables/${item.deliverable_id}`}>
                Revisar
            </Link>
        </li>
    );
}

function ProjectRow({ project }: { project: ProjectListItem }) {
    const progress =
        project.total_deliverables === 0
            ? 0
            : (project.approved_deliverables / project.total_deliverables) * 100;

    return (
        <li className="project-row">
            <div className="project-row__main">
                <h3 className="project-row__title">
                    <Link to={`/projects/${project.id}`}>{project.topic}</Link>
                </h3>
                <p className="muted">
                    {projectTypeLabels[project.project_type]} ·{' '}
                    {project.participants.map((participant) => participant.name).join(', ')}
                </p>
                <div className="progress">
                    <div
                        className="progress__bar"
                        role="progressbar"
                        aria-label={`Progreso de ${project.topic}`}
                        aria-valuemin={0}
                        aria-valuemax={project.total_deliverables}
                        aria-valuenow={project.approved_deliverables}
                        aria-valuetext={`${project.approved_deliverables} de ${project.total_deliverables} entregables aprobados`}
                    >
                        <span style={{ width: `${progress}%` }} />
                    </div>
                    <span className="muted">
                        {project.total_deliverables === 0
                            ? 'Sin entregables todavía'
                            : `${project.approved_deliverables} de ${project.total_deliverables} entregables aprobados`}
                    </span>
                </div>
            </div>
            <div className="project-row__side">
                {project.overdue_deliverables > 0 ? (
                    <span className="chip chip--overdue">
                        {project.overdue_deliverables} atrasado
                        {project.overdue_deliverables === 1 ? '' : 's'}
                    </span>
                ) : null}
                {project.my_role === 'manager' && project.pending_review_deliverables > 0 ? (
                    <span className="chip chip--submitted">
                        {project.pending_review_deliverables} por revisar
                    </span>
                ) : null}
                <p className="muted">
                    {project.next_deadline_at
                        ? `Próximo plazo: ${formatDateTime(project.next_deadline_at)}`
                        : 'Sin plazos pendientes'}
                </p>
                <p className="muted">
                    Última modificación: {formatDateTime(project.last_modified_at)}
                </p>
            </div>
        </li>
    );
}

export function ProjectsPage() {
    const me = useMe();
    const projects = useProjects();
    const pending = usePendingReviews();
    const user = me.data;

    if (!user) {
        return null;
    }

    const pendingItems = pending.data ?? [];
    const isAnyManager = projects.data?.some((project) => project.my_role === 'manager') ?? false;
    const showPending = isAnyManager || pendingItems.length > 0;

    return (
        <div className="stack">
            <div className="page-header">
                <div>
                    <h1>Hola, {firstName(user.name)}</h1>
                    <p className="lead">
                        {pendingItems.length > 0
                            ? `Tienes ${pendingItems.length} entrega${pendingItems.length === 1 ? '' : 's'} por revisar.`
                            : isAnyManager
                              ? 'No tienes entregas por revisar.'
                              : 'Revisa el estado de tus entregables, sube nuevas versiones y sigue tus plazos.'}
                    </p>
                </div>
                {user.user_type === 'professor' ? (
                    <div className="page-actions">
                        <Link className="button" to="/projects/new">
                            Nuevo proyecto
                        </Link>
                    </div>
                ) : null}
            </div>

            {showPending ? (
                <section className="panel" aria-labelledby="pending-title">
                    <div className="section-heading">
                        <h2 id="pending-title">Esperan tu revisión</h2>
                        <span className="chip chip--neutral">
                            {pendingItems.length} entrega
                            {pendingItems.length === 1 ? '' : 's'}
                        </span>
                    </div>
                    {pending.isPending ? (
                        <LoadingState />
                    ) : pending.isError ? (
                        <ErrorState message="No se pudo cargar la bandeja de revisión." />
                    ) : pendingItems.length === 0 ? (
                        <EmptyState title="No tienes entregas por revisar." />
                    ) : (
                        <ul className="pending-list">
                            {pendingItems.map((item) => (
                                <PendingReviewRow item={item} key={item.deliverable_id} />
                            ))}
                        </ul>
                    )}
                </section>
            ) : null}

            <section aria-labelledby="projects-title">
                <div className="section-heading">
                    <h2 id="projects-title">Tus proyectos</h2>
                    <p className="muted small">Ordenados por última modificación</p>
                </div>

                {projects.isPending ? (
                    <LoadingState />
                ) : projects.isError ? (
                    <ErrorState message="No se pudieron cargar los proyectos." />
                ) : projects.data.length === 0 ? (
                    <EmptyState title="Aún no tienes proyectos.">
                        {user.user_type === 'professor' ? (
                            <Link className="button" to="/projects/new">
                                Crear el primer proyecto
                            </Link>
                        ) : (
                            <p className="muted">
                                Cuando un gestor te agregue a un proyecto, aparecerá aquí.
                            </p>
                        )}
                    </EmptyState>
                ) : (
                    <ul className="project-list">
                        {projects.data.map((project) => (
                            <ProjectRow key={project.id} project={project} />
                        ))}
                    </ul>
                )}
            </section>
        </div>
    );
}
