import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError } from '../api/client';
import {
    useDeliverable,
    usePostMessage,
    useReviewDeliverable,
    useSubmitDeliverable,
} from '../api/queries';
import type { DeliverableDetail, ForumMessage, ReviewDecision, Submission } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { Feedback } from '../components/Feedback';
import { LoadingState } from '../components/LoadingState';
import { ReviewBlock } from '../components/ReviewBlock';
import { StatusChip } from '../components/StatusChip';
import { SubmissionFiles } from '../components/SubmissionFiles';
import { fileFormatLabels, formatDateTime, initials } from '../utils/format';

export function DeliverablePage() {
    const { deliverableId } = useParams<{ deliverableId: string }>();
    const deliverable = useDeliverable(deliverableId);
    const [reviewFeedback, setReviewFeedback] = useState<string | null>(null);

    if (!deliverableId) {
        return <ErrorState message="No se pudo identificar el entregable." />;
    }

    if (deliverable.isPending) {
        return <LoadingState label="Cargando entregable…" />;
    }

    if (deliverable.isError || !deliverable.data) {
        return (
            <div className="stack">
                <Link className="back-link" to="/">
                    ← Proyectos
                </Link>
                <ErrorState message="No se pudo cargar el entregable. Puede que no exista o que no tengas acceso." />
            </div>
        );
    }

    const data = deliverable.data;

    return (
        <div className="stack">
            <Link className="back-link" to={`/projects/${data.project_id}`}>
                ← Volver al proyecto
            </Link>

            <div className="page-header">
                <div>
                    <h1>{data.title}</h1>
                    <p className="lead">
                        Hito «{data.milestone_name}», {data.project_topic}.
                    </p>
                    <p className="deliverable-description">{data.description}</p>
                </div>
            </div>

            <section className="panel panel--state status-panel" aria-label="Estado del entregable">
                <div className="status-panel__text">
                    <StatusChip status={data.status} isOverdue={data.is_overdue} />
                    <p>{statusDescription(data.status)}</p>
                </div>
                <div className="status-panel__meta">
                    <p className="muted small">Fecha límite: {formatDateTime(data.deadline_at)}</p>
                    <p className="muted small">
                        {data.latest_submission
                            ? `Última entrega: versión ${data.latest_submission.version}, ${formatDateTime(data.latest_submission.submitted_at)}.`
                            : 'Sin entregas.'}
                    </p>
                </div>
            </section>

            <Feedback message={reviewFeedback} />

            <div className="detail-grid">
                <div className="detail-main stack">
                    <LatestSubmissionPanel deliverable={data} />
                    <ReviewResultPanel deliverable={data} />
                    <ManagerReviewPanel
                        deliverable={data}
                        onReviewed={() =>
                            setReviewFeedback(
                                'Revisión registrada. Puedes dejar un comentario en el foro.',
                            )
                        }
                    />
                    <UploadPanel deliverable={data} />
                    <ForumPanel deliverable={data} />
                </div>

                <aside className="detail-side">
                    <DeliverableFicha deliverable={data} />
                </aside>
            </div>
        </div>
    );
}

function statusDescription(status: DeliverableDetail['status']): string {
    if (status === 'submitted') {
        return 'La última entrega está en revisión.';
    }
    if (status === 'changes_requested') {
        return 'Se solicitaron cambios sobre la última entrega.';
    }
    if (status === 'approved') {
        return 'La última entrega fue aprobada.';
    }
    return 'El entregable está pendiente de entrega.';
}

function LatestSubmissionPanel({ deliverable }: { deliverable: DeliverableDetail }) {
    const submission = deliverable.latest_submission;

    return (
        <section className="panel" aria-labelledby="latest-submission-title">
            <div className="section-heading">
                <h2 id="latest-submission-title">Última entrega</h2>
                {submission ? (
                    <span className="chip chip--neutral">Versión {submission.version}</span>
                ) : null}
            </div>

            {submission ? (
                <SubmissionBody deliverable={deliverable} submission={submission} />
            ) : (
                <EmptyState title="Sin entregas">
                    <p className="muted">
                        Cuando se registre una entrega, aparecerá aquí con sus archivos y su estado
                        de revisión.
                    </p>
                </EmptyState>
            )}
        </section>
    );
}

function SubmissionBody({
    deliverable,
    submission,
}: {
    deliverable: DeliverableDetail;
    submission: Submission;
}) {
    return (
        <>
            <p className="muted small">
                Entregada por {submission.author_name} el {formatDateTime(submission.submitted_at)}.
            </p>

            <SubmissionFiles files={submission.files} />

            {submission.link_url ? (
                <p className="link-line">
                    Enlace de la entrega:{' '}
                    <a href={submission.link_url} target="_blank" rel="noreferrer">
                        {submission.link_url}
                    </a>
                </p>
            ) : null}

            {deliverable.my_role === 'collaborator' ? (
                <p className="panel-note">
                    Solo ves la última versión entregada. Las anteriores se conservan y el equipo
                    gestor puede verlas en el historial.
                </p>
            ) : null}

            {deliverable.my_role === 'manager' && deliverable.version_count > 0 ? (
                <p className="link-line">
                    <Link to={`/deliverables/${deliverable.id}/history`}>
                        Ver historial de versiones ({deliverable.version_count})
                    </Link>
                </p>
            ) : null}
        </>
    );
}

function ReviewResultPanel({ deliverable }: { deliverable: DeliverableDetail }) {
    return (
        <section className="panel" aria-labelledby="review-result-title">
            <div className="section-heading">
                <h2 id="review-result-title">Revisión</h2>
            </div>
            {deliverable.review ? (
                <ReviewBlock review={deliverable.review} />
            ) : (
                <p className="muted">Espera revisión.</p>
            )}
        </section>
    );
}

function ManagerReviewPanel({
    deliverable,
    onReviewed,
}: {
    deliverable: DeliverableDetail;
    onReviewed: () => void;
}) {
    const reviewDeliverable = useReviewDeliverable();
    const [decision, setDecision] = useState<ReviewDecision | null>(null);
    const [error, setError] = useState<string | null>(null);

    const latest = deliverable.latest_submission;

    if (
        deliverable.my_role !== 'manager' ||
        deliverable.status !== 'submitted' ||
        latest === null ||
        latest.review !== null
    ) {
        return null;
    }

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (decision === null) {
            setError('Selecciona una decisión para registrar la revisión.');
            return;
        }

        setError(null);
        reviewDeliverable.mutate(
            { deliverableId: deliverable.id, decision },
            {
                onSuccess: () => {
                    onReviewed();
                    setDecision(null);
                },
                onError: (mutationError) => {
                    setError(
                        mutationError instanceof ApiError
                            ? mutationError.message
                            : 'No se pudo registrar la revisión.',
                    );
                },
            },
        );
    }

    return (
        <section className="panel" aria-labelledby="your-review-title">
            <div className="section-heading">
                <h2 id="your-review-title">Tu revisión</h2>
                <span className="chip chip--submitted">Versión {latest.version}</span>
            </div>

            <p className="muted small">
                La decisión queda registrada sobre la versión {latest.version} y será visible para
                todos los participantes. Los comentarios van en el foro del entregable.
            </p>

            {error ? (
                <div className="alert" role="alert">
                    {error}
                </div>
            ) : null}

            <form className="form" onSubmit={handleSubmit}>
                <div className="review-options">
                    <label className="radio-card">
                        <input
                            type="radio"
                            name="review-decision"
                            value="approved"
                            checked={decision === 'approved'}
                            onChange={() => setDecision('approved')}
                        />
                        <span className="radio-card__body">
                            <span className="radio-card__dot" aria-hidden="true" />
                            <span>
                                <span className="radio-card__title">Aprobar la entrega</span>
                                <span className="radio-card__desc">
                                    El entregable queda aprobado y no admite nuevas versiones.
                                </span>
                            </span>
                        </span>
                    </label>

                    <label className="radio-card">
                        <input
                            type="radio"
                            name="review-decision"
                            value="changes_requested"
                            checked={decision === 'changes_requested'}
                            onChange={() => setDecision('changes_requested')}
                        />
                        <span className="radio-card__body">
                            <span className="radio-card__dot" aria-hidden="true" />
                            <span>
                                <span className="radio-card__title">Solicitar cambios</span>
                                <span className="radio-card__desc">
                                    El colaborador podrá enviar una nueva versión.
                                </span>
                            </span>
                        </span>
                    </label>
                </div>

                <div className="form__actions">
                    <button
                        className="button"
                        type="submit"
                        disabled={decision === null || reviewDeliverable.isPending}
                    >
                        {reviewDeliverable.isPending ? 'Registrando…' : 'Registrar revisión'}
                    </button>
                </div>
            </form>
        </section>
    );
}

function UploadPanel({ deliverable }: { deliverable: DeliverableDetail }) {
    const submitDeliverable = useSubmitDeliverable();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [files, setFiles] = useState<File[]>([]);
    const [linkUrl, setLinkUrl] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [feedback, setFeedback] = useState<string | null>(null);

    if (deliverable.my_role !== 'collaborator' || deliverable.status === 'approved') {
        return null;
    }

    const formatList = deliverable.allowed_formats
        .map((format) => fileFormatLabels[format])
        .join(', ');

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setFeedback(null);

        if (files.length === 0) {
            setError(`Adjunta al menos un archivo válido: ${formatList}.`);
            return;
        }

        const allowedFormats = new Set<string>(deliverable.allowed_formats);
        const invalidFile = files.find((file) => !allowedFormats.has(fileExtension(file.name)));
        if (invalidFile) {
            setError(`Adjunta al menos un archivo válido: ${formatList}.`);
            return;
        }

        const emptyFile = files.find((file) => file.size === 0);
        if (emptyFile) {
            setError(`El archivo ${emptyFile.name} está vacío.`);
            return;
        }

        const maxBytes = deliverable.max_file_size_mb * 1024 * 1024;
        const oversizedFile = files.find((file) => file.size > maxBytes);
        if (oversizedFile) {
            setError(
                `El archivo ${oversizedFile.name} supera el tamaño máximo de ${deliverable.max_file_size_mb} MB.`,
            );
            return;
        }

        const trimmedLink = linkUrl.trim();
        if (trimmedLink && !trimmedLink.startsWith('https://')) {
            setError('Ingrese un enlace HTTPS válido.');
            return;
        }

        submitDeliverable.mutate(
            { deliverableId: deliverable.id, files, linkUrl: trimmedLink },
            {
                onSuccess: (submission) => {
                    setFiles([]);
                    setLinkUrl('');
                    if (fileInputRef.current) {
                        fileInputRef.current.value = '';
                    }
                    setFeedback(
                        `Entrega enviada. La versión ${submission.version} ya está disponible.`,
                    );
                },
                onError: (mutationError) => {
                    setError(
                        mutationError instanceof ApiError
                            ? mutationError.message
                            : 'No se pudo enviar la entrega.',
                    );
                },
            },
        );
    }

    return (
        <section className="panel" aria-labelledby="new-version-title">
            <div className="section-heading">
                <h2 id="new-version-title">Entregar una nueva versión</h2>
            </div>

            <p className="muted small">
                Al enviarla, pasa a ser la versión visible del entregable y queda numerada como una
                versión nueva. La entrega anterior se conserva.
            </p>

            <form className="form" onSubmit={handleSubmit} noValidate>
                <div className="upload-zone">
                    <p className="upload-zone__text">Selecciona los archivos de tu entrega</p>
                    <p className="upload-zone__help">Se enviarán juntos como una sola versión.</p>
                    <label className="button button--secondary" htmlFor="deliverable-files">
                        Elegir archivos
                    </label>
                    <input
                        ref={fileInputRef}
                        id="deliverable-files"
                        className="file-input"
                        type="file"
                        multiple
                        accept={deliverable.allowed_formats.map((format) => `.${format}`).join(',')}
                        onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
                    />
                    <p className="file-selection" role="status">
                        {files.map((file) => file.name).join(', ')}
                    </p>
                    <p className="upload-zone__help">
                        {formatList}, hasta {deliverable.max_file_size_mb} MB por archivo.
                    </p>
                </div>

                <div className="field">
                    <label htmlFor="submission-link">Enlace de la entrega (opcional)</label>
                    <input
                        id="submission-link"
                        className="input"
                        type="url"
                        value={linkUrl}
                        onChange={(event) => setLinkUrl(event.target.value)}
                        placeholder="https://…"
                    />
                    <p className="help">
                        Debe comenzar con https://. Los archivos siguen siendo obligatorios.
                    </p>
                </div>

                <p className="panel-note">
                    Una nueva versión reemplaza la visible y conserva las anteriores.
                </p>

                {error ? (
                    <div className="alert" role="alert">
                        {error}
                    </div>
                ) : null}

                <Feedback message={feedback} />

                <div className="form__actions">
                    <button className="button" type="submit" disabled={submitDeliverable.isPending}>
                        {submitDeliverable.isPending ? 'Enviando…' : 'Enviar entrega'}
                    </button>
                </div>
            </form>
        </section>
    );
}

function ForumPanel({ deliverable }: { deliverable: DeliverableDetail }) {
    const postMessage = usePostMessage();
    const [body, setBody] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [feedback, setFeedback] = useState<string | null>(null);

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setFeedback(null);

        if (!body.trim()) {
            setError('El comentario no puede estar vacío.');
            return;
        }

        postMessage.mutate(
            { deliverableId: deliverable.id, body },
            {
                onSuccess: () => {
                    setBody('');
                    setFeedback('Mensaje publicado.');
                },
                onError: (mutationError) => {
                    setError(
                        mutationError instanceof ApiError
                            ? mutationError.message
                            : 'No se pudo publicar el mensaje.',
                    );
                },
            },
        );
    }

    return (
        <section className="panel" aria-labelledby="forum-title">
            <div className="section-heading">
                <h2 id="forum-title">Foro del entregable</h2>
                <span className="chip chip--neutral">
                    {deliverable.messages.length} mensaje
                    {deliverable.messages.length === 1 ? '' : 's'}
                </span>
            </div>

            {deliverable.messages.length === 0 ? (
                <p className="muted">
                    Aún no hay mensajes. Usa el foro para coordinar la entrega y sus revisiones.
                </p>
            ) : (
                <ul className="message-list">
                    {deliverable.messages.map((message) => (
                        <ForumMessageItem key={message.id} message={message} />
                    ))}
                </ul>
            )}

            <form className="form forum-form" onSubmit={handleSubmit} noValidate>
                <div className="field">
                    <label htmlFor="forum-message">Escribe un mensaje</label>
                    <textarea
                        id="forum-message"
                        className="textarea"
                        value={body}
                        onChange={(event) => setBody(event.target.value)}
                        placeholder="Mensaje para los participantes del proyecto"
                        maxLength={2000}
                    />
                    <p className="char-count">{body.length} / 2000</p>
                </div>

                {error ? (
                    <div className="alert" role="alert">
                        {error}
                    </div>
                ) : null}

                <Feedback message={feedback} />

                <div className="form__actions">
                    <button
                        className="button button--secondary"
                        type="submit"
                        disabled={postMessage.isPending}
                    >
                        {postMessage.isPending ? 'Publicando…' : 'Publicar mensaje'}
                    </button>
                </div>
            </form>
        </section>
    );
}

function ForumMessageItem({ message }: { message: ForumMessage }) {
    return (
        <li className="message">
            <span className="avatar" aria-hidden="true">
                {initials(message.author_name)}
            </span>
            <div>
                <p className="message__header">
                    <span className="message__author">{message.author_name}</span>
                    <span className="message__date">{formatDateTime(message.created_at)}</span>
                </p>
                <p className="message__body">{message.body}</p>
            </div>
        </li>
    );
}

function DeliverableFicha({ deliverable }: { deliverable: DeliverableDetail }) {
    return (
        <section className="panel" aria-labelledby="deliverable-ficha-title">
            <h2 id="deliverable-ficha-title">Ficha del entregable</h2>
            <dl className="ficha">
                <dt>Proyecto</dt>
                <dd>
                    <Link to={`/projects/${deliverable.project_id}`}>
                        {deliverable.project_topic}
                    </Link>
                </dd>
                <dt>Hito</dt>
                <dd>{deliverable.milestone_name}</dd>
                <dt>Fecha límite</dt>
                <dd>{formatDateTime(deliverable.deadline_at)}</dd>
                <dt>Formatos admitidos</dt>
                <dd>
                    {deliverable.allowed_formats
                        .map((format) => fileFormatLabels[format])
                        .join(', ')}
                </dd>
                <dt>Tamaño máximo</dt>
                <dd>{deliverable.max_file_size_mb} MB por archivo</dd>
                <dt>Versiones entregadas</dt>
                <dd>{deliverable.version_count}</dd>
                <dt>Última actualización</dt>
                <dd>
                    {deliverable.latest_submission
                        ? formatDateTime(deliverable.latest_submission.submitted_at)
                        : 'Sin entregas'}
                </dd>
            </dl>
        </section>
    );
}

function fileExtension(name: string): string {
    return name.split('.').pop()?.toLowerCase() ?? '';
}
