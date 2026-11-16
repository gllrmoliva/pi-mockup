import type { FileFormat, ParticipantRole, ProjectType } from '../api/types';

const dateTimeFormatter = new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'America/Santiago',
});

const dateOnlyFormatter = new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'medium',
    timeZone: 'UTC',
});

export const projectTypeLabels: Record<ProjectType, string> = {
    memoir: 'Memoria de título',
    thesis: 'Tesis',
    research: 'Proyecto de investigación',
};

export const roleLabels: Record<ParticipantRole, string> = {
    manager: 'Gestor',
    collaborator: 'Colaborador',
};

export const fileFormatLabels: Record<FileFormat, string> = {
    pdf: 'PDF',
    zip: 'ZIP',
    docx: 'DOCX',
};

export function firstName(name: string): string {
    return name.trim().split(/\s+/)[0] ?? name;
}

export function initials(name: string): string {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    return parts
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() ?? '')
        .join('');
}

export function formatDateTime(iso: string): string {
    return dateTimeFormatter.format(new Date(iso));
}

export function formatDateOnly(value: string): string {
    return dateOnlyFormatter.format(new Date(`${value}T00:00:00Z`));
}

export function formatFileSize(bytes: number): string {
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function toDateTimeLocalValue(iso: string): string {
    const date = new Date(iso);
    const pad = (value: number): string => String(value).padStart(2, '0');
    return [
        `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
        `${pad(date.getHours())}:${pad(date.getMinutes())}`,
    ].join('T');
}

export function fromDateTimeLocalValue(value: string): string {
    return value ? new Date(value).toISOString() : '';
}

export function isValidEmail(value: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}
