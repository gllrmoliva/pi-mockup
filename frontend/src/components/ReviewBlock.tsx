import type { Review } from '../api/types';
import { formatDateTime } from '../utils/format';

type ReviewBlockProps = {
    review: Review;
};

export function ReviewBlock({ review }: ReviewBlockProps) {
    const approved = review.decision === 'approved';

    return (
        <div className="review-block">
            <span className={`chip chip--${approved ? 'approved' : 'changes_requested'}`}>
                <span className="chip__dot" aria-hidden="true" />
                {approved ? 'Aprobado' : 'Cambios solicitados'}
            </span>
            <p className="muted small">
                Revisado por {review.reviewer_name} el {formatDateTime(review.reviewed_at)}
            </p>
        </div>
    );
}
