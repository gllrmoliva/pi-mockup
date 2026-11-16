type FeedbackProps = {
    message: string | null;
    tone?: 'success' | 'error';
};

export function Feedback({ message, tone = 'success' }: FeedbackProps) {
    if (!message) {
        return null;
    }

    return (
        <p className={`feedback feedback--${tone}`} role="status">
            {message}
        </p>
    );
}
