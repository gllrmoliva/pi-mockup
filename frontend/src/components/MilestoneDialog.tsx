import { useState } from 'react';
import type { FormEvent } from 'react';

import { ApiError } from '../api/client';
import { useCreateMilestone } from '../api/queries';
import { Modal } from './Modal';

type MilestoneDialogProps = {
    projectId: string;
    milestoneCount: number;
    onClose: () => void;
};

export function MilestoneDialog({ projectId, milestoneCount, onClose }: MilestoneDialogProps) {
    const createMilestone = useCreateMilestone();
    const [name, setName] = useState('');
    const [position, setPosition] = useState(String(milestoneCount + 1));
    const [error, setError] = useState<string | null>(null);

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        const trimmedName = name.trim();
        if (!trimmedName) {
            setError('El Hito debe tener un nombre.');
            return;
        }

        const parsedPosition = Number(position);
        if (
            !Number.isInteger(parsedPosition) ||
            parsedPosition < 1 ||
            parsedPosition > milestoneCount + 1
        ) {
            setError('La posición del hito no es válida.');
            return;
        }

        setError(null);
        createMilestone.mutate(
            {
                projectId,
                input: { name: trimmedName, position: parsedPosition },
            },
            {
                onSuccess: () => {
                    onClose();
                },
                onError: (mutationError) => {
                    setError(
                        mutationError instanceof ApiError
                            ? mutationError.message
                            : 'No se pudo crear el hito.',
                    );
                },
            },
        );
    }

    return (
        <Modal title="Nuevo hito" onClose={onClose}>
            {error ? (
                <div className="alert" role="alert">
                    {error}
                </div>
            ) : null}

            <form className="form" onSubmit={handleSubmit} noValidate>
                <div className="field">
                    <label htmlFor="milestone-name">Nombre del hito</label>
                    <input
                        id="milestone-name"
                        className="input"
                        type="text"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        maxLength={200}
                        required
                    />
                </div>

                <div className="field">
                    <label htmlFor="milestone-position">Ubicación</label>
                    <input
                        id="milestone-position"
                        className="input"
                        type="number"
                        min={1}
                        max={milestoneCount + 1}
                        value={position}
                        onChange={(event) => setPosition(event.target.value)}
                    />
                    <p className="help">
                        Se insertará en la posición {position || '…'} de {milestoneCount + 1}. La
                        última posición agrega el hito al final.
                    </p>
                </div>

                <div className="form__actions">
                    <button className="button button--secondary" type="button" onClick={onClose}>
                        Cancelar
                    </button>
                    <button className="button" type="submit" disabled={createMilestone.isPending}>
                        {createMilestone.isPending ? 'Creando…' : 'Crear hito'}
                    </button>
                </div>
            </form>
        </Modal>
    );
}
