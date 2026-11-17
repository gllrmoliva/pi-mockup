import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';

type ModalProps = {
    title: string;
    children: ReactNode;
    onClose: () => void;
};

export function Modal({ title, children, onClose }: ModalProps) {
    const dialogRef = useRef<HTMLDialogElement>(null);
    const previouslyFocused = useRef<HTMLElement | null>(null);
    const titleId = useId();

    useEffect(() => {
        const dialog = dialogRef.current;
        if (dialog === null) {
            return;
        }
        previouslyFocused.current = document.activeElement as HTMLElement | null;
        if (!dialog.open) {
            dialog.showModal();
        }
        return () => {
            if (dialog.open) {
                dialog.close();
            }
            if (previouslyFocused.current?.isConnected) {
                previouslyFocused.current.focus({ preventScroll: true });
            }
        };
    }, []);

    return (
        <dialog
            ref={dialogRef}
            className="dialog"
            aria-labelledby={titleId}
            onCancel={(event) => {
                event.preventDefault();
                onClose();
            }}
            onClick={(event) => {
                if (event.target === event.currentTarget) {
                    onClose();
                }
            }}
        >
            <div className="dialog__header">
                <h2 id={titleId}>{title}</h2>
                <button
                    className="dialog__close"
                    type="button"
                    aria-label="Cerrar"
                    onClick={onClose}
                >
                    ×
                </button>
            </div>
            <div className="dialog__body">{children}</div>
        </dialog>
    );
}
