import { useId, useState } from 'react';
import type { FormEvent } from 'react';

import { ApiError } from '../api/client';
import { useCreateDeliverable, useDeliverable, useUpdateDeliverable } from '../api/queries';
import type { DeliverableDetail, DeliverableInput, FileFormat } from '../api/types';
import { fileFormatLabels, fromDateTimeLocalValue, toDateTimeLocalValue } from '../utils/format';
import { ErrorState } from './ErrorState';
import { LoadingState } from './LoadingState';
import { Modal } from './Modal';

const fileFormats: FileFormat[] = ['pdf', 'zip', 'docx'];

function isPastDateTime(value: string): boolean {
    return value !== '' && new Date(value).getTime() <= Date.now();
}

type FieldErrors = {
    title?: string;
    description?: string;
    deadline?: string;
    formats?: string;
    size?: string;
};

type DeliverableDialogProps = {
    milestoneId?: string;
    deliverableId?: string;
    onClose: () => void;
};

export function DeliverableDialog({ milestoneId, deliverableId, onClose }: DeliverableDialogProps) {
    const deliverable = useDeliverable(deliverableId);

    if (deliverableId) {
        if (deliverable.isPending) {
            return (
                <Modal title="Editar entregable" onClose={onClose}>
                    <LoadingState label="Cargando entregable…" />
                </Modal>
            );
        }

        if (deliverable.isError || !deliverable.data) {
            return (
                <Modal title="Editar entregable" onClose={onClose}>
                    <ErrorState message="No se pudo cargar el entregable." />
                </Modal>
            );
        }

        return (
            <DeliverableForm deliverable={deliverable.data} milestoneId={null} onClose={onClose} />
        );
    }

    return <DeliverableForm milestoneId={milestoneId ?? null} onClose={onClose} />;
}

type DeliverableFormProps = {
    milestoneId: string | null;
    deliverable?: DeliverableDetail;
    onClose: () => void;
};

function DeliverableForm({ milestoneId, deliverable, onClose }: DeliverableFormProps) {
    const createDeliverable = useCreateDeliverable();
    const updateDeliverable = useUpdateDeliverable();
    const baseId = useId();
    const titleId = `${baseId}-title`;
    const titleErrorId = `${baseId}-title-error`;
    const descriptionId = `${baseId}-description`;
    const descriptionErrorId = `${baseId}-description-error`;
    const deadlineId = `${baseId}-deadline`;
    const deadlineHelpId = `${baseId}-deadline-help`;
    const deadlineErrorId = `${baseId}-deadline-error`;
    const formatsId = `${baseId}-formats`;
    const formatsErrorId = `${baseId}-formats-error`;
    const sizeId = `${baseId}-size`;
    const sizeHelpId = `${baseId}-size-help`;
    const sizeErrorId = `${baseId}-size-error`;

    const initialDeadline = deliverable ? toDateTimeLocalValue(deliverable.deadline_at) : '';
    const [title, setTitle] = useState(deliverable?.title ?? '');
    const [description, setDescription] = useState(deliverable?.description ?? '');
    const [deadline, setDeadline] = useState(initialDeadline);
    const [formats, setFormats] = useState<FileFormat[]>(
        deliverable?.allowed_formats ?? [...fileFormats],
    );
    const [maxSize, setMaxSize] = useState(String(deliverable?.max_file_size_mb ?? 50));
    const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
    const [serverError, setServerError] = useState<string | null>(null);

    const isEditing = deliverable !== undefined;
    const isPending = createDeliverable.isPending || updateDeliverable.isPending;
    const pastDeadline = isPastDateTime(initialDeadline);

    function toggleFormat(format: FileFormat, checked: boolean) {
        setFormats((current) =>
            checked ? [...current, format] : current.filter((item) => item !== format),
        );
    }

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setServerError(null);

        const trimmedTitle = title.trim();
        const trimmedDescription = description.trim();
        const nextErrors: FieldErrors = {};
        const requiredMessage = 'Los campos no pueden estar vacíos.';

        if (!trimmedTitle) {
            nextErrors.title = requiredMessage;
        }
        if (!trimmedDescription) {
            nextErrors.description = requiredMessage;
        }
        if (formats.length === 0) {
            nextErrors.formats = requiredMessage;
        }

        let deadlineAt = '';
        const deadlineTimestamp = deadline ? new Date(deadline).getTime() : Number.NaN;
        if (!deadline || Number.isNaN(deadlineTimestamp)) {
            nextErrors.deadline = 'Ingrese una fecha de entrega válida.';
        } else if (deliverable && deadline === initialDeadline) {
            deadlineAt = deliverable.deadline_at;
        } else if (deadlineTimestamp <= Date.now()) {
            nextErrors.deadline = 'Ingrese una fecha de entrega válida.';
        } else {
            deadlineAt = fromDateTimeLocalValue(deadline);
        }

        const parsedMaxSize = Number(maxSize);
        if (!Number.isInteger(parsedMaxSize) || parsedMaxSize < 1 || parsedMaxSize > 200) {
            nextErrors.size = 'El tamaño máximo debe estar entre 1 y 200 MB.';
        }

        if (Object.keys(nextErrors).length > 0) {
            setFieldErrors(nextErrors);
            return;
        }

        setFieldErrors({});
        const input: DeliverableInput = {
            title: trimmedTitle,
            description: trimmedDescription,
            deadline_at: deadlineAt,
            allowed_formats: formats,
            max_file_size_mb: parsedMaxSize,
        };

        if (deliverable) {
            updateDeliverable.mutate(
                { deliverableId: deliverable.id, input },
                {
                    onSuccess: () => {
                        onClose();
                    },
                    onError: (mutationError) => {
                        setServerError(
                            mutationError instanceof ApiError
                                ? mutationError.message
                                : 'No se pudo guardar el entregable.',
                        );
                    },
                },
            );
            return;
        }

        if (!milestoneId) {
            setServerError('No se pudo identificar el hito del entregable.');
            return;
        }

        createDeliverable.mutate(
            { milestoneId, input },
            {
                onSuccess: () => {
                    onClose();
                },
                onError: (mutationError) => {
                    setServerError(
                        mutationError instanceof ApiError
                            ? mutationError.message
                            : 'No se pudo crear el entregable.',
                    );
                },
            },
        );
    }

    return (
        <Modal title={isEditing ? 'Editar entregable' : 'Nuevo entregable'} onClose={onClose}>
            {serverError ? (
                <div className="alert" role="alert">
                    {serverError}
                </div>
            ) : null}

            <form className="form" onSubmit={handleSubmit} noValidate>
                <div className="field">
                    <label htmlFor={titleId}>Nombre del entregable</label>
                    <input
                        id={titleId}
                        className="input"
                        type="text"
                        value={title}
                        onChange={(event) => setTitle(event.target.value)}
                        maxLength={200}
                        aria-invalid={Boolean(fieldErrors.title)}
                        aria-describedby={fieldErrors.title ? titleErrorId : undefined}
                        required
                    />
                    {fieldErrors.title ? (
                        <p className="field__error" id={titleErrorId}>
                            {fieldErrors.title}
                        </p>
                    ) : null}
                </div>

                <div className="field">
                    <label htmlFor={descriptionId}>Descripción</label>
                    <textarea
                        id={descriptionId}
                        className="textarea"
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                        maxLength={4000}
                        aria-invalid={Boolean(fieldErrors.description)}
                        aria-describedby={fieldErrors.description ? descriptionErrorId : undefined}
                        required
                    />
                    {fieldErrors.description ? (
                        <p className="field__error" id={descriptionErrorId}>
                            {fieldErrors.description}
                        </p>
                    ) : null}
                </div>

                <div className="field">
                    <label htmlFor={deadlineId}>Fecha y hora límite</label>
                    <input
                        id={deadlineId}
                        className="input"
                        type="datetime-local"
                        value={deadline}
                        onChange={(event) => setDeadline(event.target.value)}
                        aria-invalid={Boolean(fieldErrors.deadline)}
                        aria-describedby={
                            fieldErrors.deadline
                                ? `${deadlineHelpId} ${deadlineErrorId}`
                                : deadlineHelpId
                        }
                        required
                    />
                    <p className="help" id={deadlineHelpId}>
                        {pastDeadline
                            ? 'La fecha ya pasó. Puedes editar otros campos sin cambiarla.'
                            : 'La fecha y hora se guardan con tu zona horaria.'}
                    </p>
                    {fieldErrors.deadline ? (
                        <p className="field__error" id={deadlineErrorId}>
                            {fieldErrors.deadline}
                        </p>
                    ) : null}
                </div>

                <div className="field">
                    <p className="field__label" id={formatsId}>
                        Formatos admitidos
                    </p>
                    <div
                        className="format-grid"
                        aria-labelledby={formatsId}
                        aria-describedby={fieldErrors.formats ? formatsErrorId : undefined}
                    >
                        {fileFormats.map((format) => (
                            <label className="checkbox" key={format}>
                                <input
                                    type="checkbox"
                                    checked={formats.includes(format)}
                                    onChange={(event) => toggleFormat(format, event.target.checked)}
                                />
                                {fileFormatLabels[format]}
                            </label>
                        ))}
                    </div>
                    {fieldErrors.formats ? (
                        <p className="field__error" id={formatsErrorId}>
                            {fieldErrors.formats}
                        </p>
                    ) : null}
                </div>

                <div className="field">
                    <label htmlFor={sizeId}>Tamaño máximo por archivo (MB)</label>
                    <input
                        id={sizeId}
                        className="input"
                        type="number"
                        min={1}
                        max={200}
                        value={maxSize}
                        onChange={(event) => setMaxSize(event.target.value)}
                        aria-invalid={Boolean(fieldErrors.size)}
                        aria-describedby={
                            fieldErrors.size ? `${sizeHelpId} ${sizeErrorId}` : sizeHelpId
                        }
                    />
                    <p className="help" id={sizeHelpId}>
                        Entre 1 y 200 MB por archivo.
                    </p>
                    {fieldErrors.size ? (
                        <p className="field__error" id={sizeErrorId}>
                            {fieldErrors.size}
                        </p>
                    ) : null}
                </div>

                <div className="form__actions">
                    <button className="button button--secondary" type="button" onClick={onClose}>
                        Cancelar
                    </button>
                    <button className="button" type="submit" disabled={isPending}>
                        {isPending
                            ? 'Guardando…'
                            : isEditing
                              ? 'Guardar entregable'
                              : 'Crear entregable'}
                    </button>
                </div>
            </form>
        </Modal>
    );
}
