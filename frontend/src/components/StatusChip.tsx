import type { DeliverableStatus } from '../api/types';

const statusLabels: Record<DeliverableStatus, string> = {
    pending: 'Pendiente',
    submitted: 'Entregado',
    changes_requested: 'Cambios solicitados',
    approved: 'Aprobado',
};

type StatusChipProps = {
    status: DeliverableStatus;
    isOverdue?: boolean;
};

export function StatusChip({ status, isOverdue = false }: StatusChipProps) {
    return (
        <span className="chip-group">
            <span className={`chip chip--${status}`}>
                <span className="chip__dot" aria-hidden="true" />
                {statusLabels[status]}
            </span>
            {isOverdue ? (
                <span className="chip chip--overdue">
                    <span className="chip__dot" aria-hidden="true" />
                    Atrasado
                </span>
            ) : null}
        </span>
    );
}
