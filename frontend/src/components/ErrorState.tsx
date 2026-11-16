type ErrorStateProps = {
    message: string;
};

export function ErrorState({ message }: ErrorStateProps) {
    return (
        <div className="alert" role="alert">
            {message}
        </div>
    );
}
