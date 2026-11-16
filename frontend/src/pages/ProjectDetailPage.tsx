import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useProject } from '../api/queries';
import type { DeliverableSummary, Milestone } from '../api/types';
import { DeliverableDialog } from '../components/DeliverableDialog';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { MilestoneDialog } from '../components/MilestoneDialog';
import { ParticipantChips } from '../components/ParticipantChips';
import { StatusChip } from '../components/StatusChip';
import { formatDateOnly, formatDateTime, projectTypeLabels } from '../utils/format';

type DeliverableDialogState =
    { mode: 'create'; milestoneId: string } | { mode: 'edit'; deliverableId: string } | null;

export function ProjectDetailPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const project = useProject(projectId);
    const [milestoneDialogOpen, setMilestoneDialogOpen] = useState(false);
    const [deliverableDialog, setDeliverableDialog] = useState<DeliverableDialogState>(null);

    if (!projectId) {
        return <ErrorState message="No se pudo identificar el proyecto." />;
    }

    if (project.isPending) {
        return <LoadingState label="Cargando proyecto…" />;
    }

    if (project.isError || !project.data) {
        return (
            <div className="stack">
                <Link className="back-link" to="/">
                    ← Proyectos
                </Link>
                <ErrorState message="No se pudo cargar el proyecto. Puede que no exista o que no tengas acceso." />
            </div>
        );
    }

    const data = project.data;
    const isManager = data.my_role === 'manager';

    return (
        <div className="stack">
            <Link className="back-link" to="/">
                ← Proyectos
            </Link>

            <div className="page-header">
                <div>
                    <h1>{data.topic}</h1>
                    <p className="lead">
                        {projectTypeLabels[data.project_type]} · Iniciado el{' '}
                        {formatDateOnly(data.started_on)} · Última modificación:{' '}
                        {formatDateTime(data.last_modified_at)}
                    </p>
                    <ParticipantChips participants={data.participants} />
                </div>
                {isManager ? (
                    <div className="page-actions">
                        <Link className="button button--secondary" to={`/projects/${data.id}/edit`}>
                            Editar proyecto
                        </Link>
                        <button
                            className="button"
                            type="button"
                            onClick={() => setMilestoneDialogOpen(true)}
                        >
                            Nuevo hito
                        </button>
                    </div>
                ) : null}
            </div>

            <section className="panel" aria-labelledby="milestones-title">
                <div className="section-heading">
                    <h2 id="milestones-title">Hitos y entregables</h2>
                    {data.milestones.length > 0 ? (
                        <span className="chip chip--neutral">
                            {data.milestones.length} hito
                            {data.milestones.length === 1 ? '' : 's'}
                        </span>
                    ) : null}
                </div>

                {data.milestones.length === 0 ? (
                    <EmptyState title="No existen hitos para este proyecto">
                        {isManager ? (
                            <>
                                <p className="muted">
                                    Crea el primer hito para empezar a definir entregables y fechas.
                                </p>
                                <button
                                    className="button"
                                    type="button"
                                    onClick={() => setMilestoneDialogOpen(true)}
                                >
                                    Crear el primer hito
                                </button>
                            </>
                        ) : (
                            <p className="muted">
                                Cuando el equipo gestor defina los hitos, aparecerán aquí.
                            </p>
                        )}
                    </EmptyState>
                ) : (
                    <ol className="timeline">
                        {data.milestones.map((milestone) => (
                            <MilestoneItem
                                isManager={isManager}
                                key={milestone.id}
                                milestone={milestone}
                                onCreateDeliverable={(milestoneId) =>
                                    setDeliverableDialog({
                                        mode: 'create',
                                        milestoneId,
                                    })
                                }
                                onEditDeliverable={(deliverableId) =>
                                    setDeliverableDialog({
                                        mode: 'edit',
                                        deliverableId,
                                    })
                                }
                            />
                        ))}
                    </ol>
                )}
            </section>

            {milestoneDialogOpen ? (
                <MilestoneDialog
                    projectId={data.id}
                    milestoneCount={data.milestones.length}
                    onClose={() => setMilestoneDialogOpen(false)}
                />
            ) : null}

            {deliverableDialog?.mode === 'create' ? (
                <DeliverableDialog
                    milestoneId={deliverableDialog.milestoneId}
                    onClose={() => setDeliverableDialog(null)}
                />
            ) : null}

            {deliverableDialog?.mode === 'edit' ? (
                <DeliverableDialog
                    deliverableId={deliverableDialog.deliverableId}
                    onClose={() => setDeliverableDialog(null)}
                />
            ) : null}
        </div>
    );
}

type MilestoneItemProps = {
    milestone: Milestone;
    isManager: boolean;
    onCreateDeliverable: (milestoneId: string) => void;
    onEditDeliverable: (deliverableId: string) => void;
};

function MilestoneItem({
    milestone,
    isManager,
    onCreateDeliverable,
    onEditDeliverable,
}: MilestoneItemProps) {
    const approved = milestone.deliverables.filter(
        (deliverable) => deliverable.status === 'approved',
    ).length;

    return (
        <li className="milestone">
            <span className="milestone__marker" aria-hidden="true">
                {milestone.order_index}
            </span>

            <div className="milestone__header">
                <h3 className="milestone__title">{milestone.name}</h3>
                {isManager ? (
                    <div className="milestone__actions">
                        <button
                            className="button button--ghost"
                            type="button"
                            onClick={() => onCreateDeliverable(milestone.id)}
                        >
                            Nuevo entregable
                        </button>
                    </div>
                ) : null}
            </div>

            <p className="milestone__progress">
                {approved} de {milestone.deliverables.length} entregables aprobados
            </p>

            {milestone.deliverables.length === 0 ? (
                <p className="muted small">Este hito aún no tiene entregables.</p>
            ) : (
                <ul className="deliverable-list">
                    {milestone.deliverables.map((deliverable) => (
                        <DeliverableItem
                            deliverable={deliverable}
                            isManager={isManager}
                            key={deliverable.id}
                            onEditDeliverable={onEditDeliverable}
                        />
                    ))}
                </ul>
            )}
        </li>
    );
}

type DeliverableItemProps = {
    deliverable: DeliverableSummary;
    isManager: boolean;
    onEditDeliverable: (deliverableId: string) => void;
};

function DeliverableItem({ deliverable, isManager, onEditDeliverable }: DeliverableItemProps) {
    const submission = deliverable.latest_submission;

    return (
        <li className="deliverable-row">
            <div>
                <p className="deliverable-row__title">
                    <Link to={`/deliverables/${deliverable.id}`}>{deliverable.title}</Link>
                </p>
                <p
                    className={
                        deliverable.is_overdue
                            ? 'deliverable-row__deadline deliverable-row__deadline--overdue'
                            : 'deliverable-row__deadline'
                    }
                >
                    {deliverable.is_overdue ? 'Venció el ' : 'Vence el '}
                    {formatDateTime(deliverable.deadline_at)}
                </p>
                <p className="deliverable-row__meta">
                    {submission
                        ? `Última entrega: versión ${submission.version}, ${formatDateTime(submission.submitted_at)}.`
                        : 'Sin entregas.'}
                </p>
            </div>

            <div className="deliverable-row__status">
                <StatusChip status={deliverable.status} isOverdue={deliverable.is_overdue} />
            </div>

            {isManager ? (
                <div className="deliverable-row__actions">
                    {deliverable.status === 'submitted' ? (
                        <Link
                            className="button button--small"
                            to={`/deliverables/${deliverable.id}`}
                        >
                            Revisar
                        </Link>
                    ) : null}
                    <button
                        className="button button--ghost"
                        type="button"
                        onClick={() => onEditDeliverable(deliverable.id)}
                    >
                        Editar
                    </button>
                </div>
            ) : null}
        </li>
    );
}
