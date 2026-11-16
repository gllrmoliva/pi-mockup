type LoadingStateProps = {
    label?: string;
};

export function LoadingState({ label = 'Cargando…' }: LoadingStateProps) {
    return (
        <p className="loading" role="status" aria-live="polite">
            {label}
        </p>
    );
}
