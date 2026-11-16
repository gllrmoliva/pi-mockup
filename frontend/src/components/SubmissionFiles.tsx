import { fileDownloadUrl } from '../api/client';
import type { SubmissionFile } from '../api/types';
import { formatFileSize } from '../utils/format';

type SubmissionFilesProps = {
    files: SubmissionFile[];
};

export function SubmissionFiles({ files }: SubmissionFilesProps) {
    if (files.length === 0) {
        return null;
    }

    return (
        <ul className="file-list">
            {files.map((file) => (
                <li className="file-row" key={file.id}>
                    <div className="file-row__main">
                        <p className="file-row__name">{file.original_name}</p>
                        <p className="file-row__meta">
                            {file.mime_type} · {formatFileSize(file.size_bytes)} · SHA-256{' '}
                            {file.sha256.slice(0, 12)}…
                        </p>
                    </div>
                    <a
                        className="button button--secondary button--small"
                        href={fileDownloadUrl(file.id)}
                    >
                        Descargar
                    </a>
                </li>
            ))}
        </ul>
    );
}
