import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';

import { ApiError } from '../api/client';
import { useCreateProject, useMe, useProject, useUpdateProject } from '../api/queries';
import type { Participant, ParticipantRole, ProjectDetail, ProjectType, User } from '../api/types';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { isValidEmail, projectTypeLabels, roleLabels } from '../utils/format';

const projectTypes: ProjectType[] = ['memoir', 'thesis', 'research'];

type ParticipantEntry = {
    email: string;
    name: string | null;
};

type ProjectFormPageProps = {
    mode: 'create' | 'edit';
};

export function ProjectFormPage({ mode }: ProjectFormPageProps) {
    const me = useMe();
    const { projectId } = useParams<{ projectId: string }>();
    const project = useProject(mode === 'edit' ? projectId : undefined);

    if (!me.data) {
        return null;
    }

    if (mode === 'create') {
        if (me.data.user_type !== 'professor') {
            return <Navigate to="/" replace />;
        }
        return <ProjectForm mode="create" user={me.data} />;
    }

    if (!projectId) {
        return <Navigate to="/" replace />;
    }

    if (project.isPending) {
        return <LoadingState label="Cargando proyecto…" />;
    }

    if (project.isError || !project.data) {
        return (
            <div className="stack">
                <Link className="back-link" to={`/projects/${projectId}`}>
                    ← Volver al proyecto
                </Link>
                <ErrorState message="No se pudo cargar el proyecto para editarlo." />
            </div>
        );
    }

    if (project.data.my_role !== 'manager') {
        return <Navigate to={`/projects/${projectId}`} replace />;
    }

    return <ProjectForm mode="edit" project={project.data} user={me.data} />;
}

type ProjectFormProps = {
    mode: 'create' | 'edit';
    user: User;
    project?: ProjectDetail;
};

function ProjectForm({ mode, user, project }: ProjectFormProps) {
    const navigate = useNavigate();
    const createProject = useCreateProject();
    const updateProject = useUpdateProject();
    const [topic, setTopic] = useState(project?.topic ?? '');
    const [projectType, setProjectType] = useState<ProjectType>(project?.project_type ?? 'memoir');
    const [managers, setManagers] = useState<ParticipantEntry[]>(() =>
        participantsByRole(project, 'manager'),
    );
    const [collaborators, setCollaborators] = useState<ParticipantEntry[]>(() =>
        participantsByRole(project, 'collaborator'),
    );
    const [managerEmail, setManagerEmail] = useState('');
    const [collaboratorEmail, setCollaboratorEmail] = useState('');
    const [participantError, setParticipantError] = useState<string | null>(null);
    const [formError, setFormError] = useState<string | null>(null);

    const isCreate = mode === 'create';
    const selfEmail = user.email.toLowerCase();
    const wasManager =
        project?.participants.some(
            (participant) =>
                participant.email.toLowerCase() === selfEmail && participant.role === 'manager',
        ) ?? false;
    const selfIsManager = managers.some((participant) => participant.email === selfEmail);
    const selfIsCollaborator = collaborators.some((participant) => participant.email === selfEmail);
    const isEditing = project !== undefined;
    const isPending = createProject.isPending || updateProject.isPending;

    function addParticipant(role: ParticipantRole) {
        const source = role === 'manager' ? managerEmail : collaboratorEmail;
        const email = source.trim().toLowerCase();

        if (!email) {
            return;
        }

        if (!isValidEmail(email)) {
            setParticipantError('Ingresa un correo electrónico válido.');
            return;
        }

        if (
            managers.some((participant) => participant.email === email) ||
            collaborators.some((participant) => participant.email === email) ||
            (isCreate && email === selfEmail)
        ) {
            setParticipantError('Ese correo ya está en el proyecto.');
            return;
        }

        if (role === 'manager') {
            setManagers((current) => [...current, { email, name: null }]);
            setManagerEmail('');
        } else {
            setCollaborators((current) => [...current, { email, name: null }]);
            setCollaboratorEmail('');
        }
        setParticipantError(null);
    }

    function removeParticipant(role: ParticipantRole, email: string) {
        if (role === 'manager') {
            setManagers((current) => current.filter((participant) => participant.email !== email));
        } else {
            setCollaborators((current) =>
                current.filter((participant) => participant.email !== email),
            );
        }
        setParticipantError(null);
    }

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setFormError(null);
        setParticipantError(null);

        if (!topic.trim()) {
            setFormError('El tema del proyecto no puede estar vacío.');
            return;
        }

        const totalManagers = managers.length + (isCreate ? 1 : 0);
        if (totalManagers === 0) {
            setFormError('El proyecto requiere tener al menos un gestor.');
            return;
        }

        if (collaborators.length === 0) {
            setFormError('El proyecto requiere tener al menos un colaborador.');
            return;
        }

        if (managerEmail.trim() || collaboratorEmail.trim()) {
            setParticipantError('Agrega el correo pendiente antes de guardar el proyecto.');
            return;
        }

        const input = {
            topic: topic.trim(),
            project_type: projectType,
            manager_emails: managers.map((participant) => participant.email),
            collaborator_emails: collaborators.map((participant) => participant.email),
        };

        if (project) {
            updateProject.mutate(
                { projectId: project.id, input },
                {
                    onSuccess: () => {
                        const selfStillParticipant =
                            managers.some((participant) => participant.email === selfEmail) ||
                            collaborators.some((participant) => participant.email === selfEmail);
                        navigate(selfStillParticipant ? `/projects/${project.id}` : '/', {
                            replace: true,
                        });
                    },
                    onError: handleMutationError,
                },
            );
            return;
        }

        createProject.mutate(input, {
            onSuccess: (created) => {
                navigate(`/projects/${created.id}`, { replace: true });
            },
            onError: handleMutationError,
        });
    }

    function handleMutationError(error: unknown) {
        setFormError(error instanceof ApiError ? error.message : 'No se pudo guardar el proyecto.');
    }

    return (
        <div className="stack form-narrow">
            <Link className="back-link" to={project ? `/projects/${project.id}` : '/'}>
                {project ? '← Volver al proyecto' : '← Proyectos'}
            </Link>

            <div className="page-header">
                <div>
                    <h1>{isCreate ? 'Nuevo proyecto' : 'Editar proyecto'}</h1>
                    <p className="lead">
                        {isCreate
                            ? 'Define el tema, el tipo de trabajo y las personas que participarán.'
                            : 'Actualiza la información y los participantes del proyecto.'}
                    </p>
                </div>
            </div>

            <form className="panel form" onSubmit={handleSubmit} noValidate>
                {formError ? (
                    <div className="alert" role="alert">
                        {formError}
                    </div>
                ) : null}

                <div className="field">
                    <label htmlFor="project-topic">Tema del proyecto</label>
                    <input
                        id="project-topic"
                        className="input"
                        type="text"
                        value={topic}
                        onChange={(event) => setTopic(event.target.value)}
                        maxLength={300}
                        required
                    />
                </div>

                <div className="field">
                    <label htmlFor="project-type">Tipo de proyecto</label>
                    <select
                        id="project-type"
                        className="select"
                        value={projectType}
                        onChange={(event) => setProjectType(event.target.value as ProjectType)}
                    >
                        {projectTypes.map((type) => (
                            <option key={type} value={type}>
                                {projectTypeLabels[type]}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="form-section">
                    <div>
                        <p className="field__label">Gestores</p>
                        <p className="help">
                            Pueden editar el proyecto, sus hitos y sus entregables, y registrar
                            revisiones.
                        </p>
                    </div>

                    <div className="participant-editor">
                        <ul className="email-chips">
                            {isCreate ? (
                                <li className="email-chip email-chip--fixed">
                                    <span className="email-chip__main">
                                        <span className="email-chip__name">Tú</span>
                                        <span className="email-chip__email">{user.email}</span>
                                    </span>
                                    <span className="email-chip__role">Gestor</span>
                                </li>
                            ) : null}
                            {managers.map((participant) => (
                                <EmailChip
                                    key={participant.email}
                                    participant={participant}
                                    role="manager"
                                    isSelf={participant.email === selfEmail}
                                    onRemove={() => removeParticipant('manager', participant.email)}
                                />
                            ))}
                        </ul>

                        <div className="inline-add">
                            <input
                                className="input"
                                type="email"
                                value={managerEmail}
                                onChange={(event) => setManagerEmail(event.target.value)}
                                placeholder="correo@udec.cl"
                                aria-label="Correo del gestor"
                                onKeyDown={(event) => {
                                    if (event.key === 'Enter') {
                                        event.preventDefault();
                                        addParticipant('manager');
                                    }
                                }}
                            />
                            <button
                                className="button button--secondary"
                                type="button"
                                onClick={() => addParticipant('manager')}
                            >
                                Agregar gestor
                            </button>
                        </div>
                    </div>
                </div>

                <div className="form-section">
                    <div>
                        <p className="field__label">Colaboradores</p>
                        <p className="help">
                            Pueden entregar versiones de los entregables y participar en el foro.
                        </p>
                    </div>

                    <div className="participant-editor">
                        <ul className="email-chips">
                            {collaborators.length === 0 ? (
                                <li className="muted small">Aún no hay colaboradores.</li>
                            ) : null}
                            {collaborators.map((participant) => (
                                <EmailChip
                                    key={participant.email}
                                    participant={participant}
                                    role="collaborator"
                                    isSelf={participant.email === selfEmail}
                                    onRemove={() =>
                                        removeParticipant('collaborator', participant.email)
                                    }
                                />
                            ))}
                        </ul>

                        <div className="inline-add">
                            <input
                                className="input"
                                type="email"
                                value={collaboratorEmail}
                                onChange={(event) => setCollaboratorEmail(event.target.value)}
                                placeholder="correo@udec.cl"
                                aria-label="Correo del colaborador"
                                onKeyDown={(event) => {
                                    if (event.key === 'Enter') {
                                        event.preventDefault();
                                        addParticipant('collaborator');
                                    }
                                }}
                            />
                            <button
                                className="button button--secondary"
                                type="button"
                                onClick={() => addParticipant('collaborator')}
                            >
                                Agregar colaborador
                            </button>
                        </div>
                    </div>
                </div>

                {participantError ? (
                    <p className="field__error" role="alert">
                        {participantError}
                    </p>
                ) : null}

                <p className="help">
                    Solo puedes agregar cuentas activas. Las invitaciones llegarán en una versión
                    posterior.
                </p>

                {isEditing && wasManager && !selfIsManager ? (
                    <p className="warning" role="status">
                        {selfIsCollaborator
                            ? 'Si guardas, dejarás de ser gestor de este proyecto.'
                            : 'Si guardas, dejarás de ser gestor y perderás el acceso a este proyecto.'}
                    </p>
                ) : null}

                <div className="form__actions">
                    <Link
                        className="button button--secondary"
                        to={project ? `/projects/${project.id}` : '/'}
                    >
                        Cancelar
                    </Link>
                    <button className="button" type="submit" disabled={isPending}>
                        {isPending ? 'Guardando…' : isCreate ? 'Crear proyecto' : 'Guardar cambios'}
                    </button>
                </div>
            </form>
        </div>
    );
}

function participantsByRole(
    project: ProjectDetail | undefined,
    role: ParticipantRole,
): ParticipantEntry[] {
    return (project?.participants ?? [])
        .filter((participant: Participant) => participant.role === role)
        .map((participant) => ({
            email: participant.email.toLowerCase(),
            name: participant.name,
        }));
}

type EmailChipProps = {
    participant: ParticipantEntry;
    role: ParticipantRole;
    isSelf: boolean;
    onRemove: () => void;
};

function EmailChip({ participant, role, isSelf, onRemove }: EmailChipProps) {
    return (
        <li className="email-chip">
            <span className="email-chip__main">
                <span className="email-chip__name">
                    {participant.name ?? participant.email}
                    {isSelf ? ' (tú)' : ''}
                </span>
                {participant.name ? (
                    <span className="email-chip__email">{participant.email}</span>
                ) : null}
            </span>
            <span className="email-chip__role">{roleLabels[role]}</span>
            <button
                className="email-chip__remove"
                type="button"
                aria-label={`Quitar a ${participant.name ?? participant.email}`}
                onClick={onRemove}
            >
                ×
            </button>
        </li>
    );
}
