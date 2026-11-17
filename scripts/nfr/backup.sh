#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT_DIR"

BACKUP_DIR=${BACKUP_DIR:-"$ROOT_DIR/backups"}
RETENTION_DAYS=${RETENTION_DAYS:-30}
mkdir -p "$BACKUP_DIR"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
db_file="db-$timestamp.dump"
uploads_file="uploads-$timestamp.tar.gz"
manifest_file="manifest-$timestamp.json"

echo "==> Dumping PostgreSQL"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    > "$BACKUP_DIR/$db_file"
[ -s "$BACKUP_DIR/$db_file" ] || {
    echo "The PostgreSQL dump is empty." >&2
    exit 1
}

echo "==> Archiving uploads"
docker compose exec -T backend tar --sparse -czf - -C /app/uploads . \
    > "$BACKUP_DIR/$uploads_file"
[ -s "$BACKUP_DIR/$uploads_file" ] || {
    echo "The uploads archive is empty." >&2
    exit 1
}

echo "==> Collecting backup metadata"
counts=$(
    docker compose exec -T db sh -c \
        'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
SELECT json_build_object(
    'usuario', (SELECT count(*) FROM usuario),
    'proyecto', (SELECT count(*) FROM proyecto),
    'participacion', (SELECT count(*) FROM participacion),
    'hito', (SELECT count(*) FROM hito),
    'entregable', (SELECT count(*) FROM entregable),
    'entrega', (SELECT count(*) FROM entrega),
    'archivo', (SELECT count(*) FROM archivo),
    'revision', (SELECT count(*) FROM revision),
    'comentario', (SELECT count(*) FROM comentario)
);
SQL
)

uploads_count=$(
    docker compose exec -T backend sh -c 'find /app/uploads -type f | wc -l' \
        | tr -d '[:space:]'
)
db_sha=$(sha256sum "$BACKUP_DIR/$db_file" | cut -d' ' -f1)
uploads_sha=$(sha256sum "$BACKUP_DIR/$uploads_file" | cut -d' ' -f1)
db_bytes=$(wc -c < "$BACKUP_DIR/$db_file" | tr -d '[:space:]')
uploads_bytes=$(wc -c < "$BACKUP_DIR/$uploads_file" | tr -d '[:space:]')

python3 - \
    "$BACKUP_DIR/$manifest_file" \
    "$timestamp" \
    "$db_file" \
    "$db_sha" \
    "$db_bytes" \
    "$uploads_file" \
    "$uploads_sha" \
    "$uploads_bytes" \
    "$uploads_count" \
    "$counts" <<'PY'
import json
import sys

(
    manifest_path,
    timestamp,
    db_file,
    db_sha,
    db_bytes,
    uploads_file,
    uploads_sha,
    uploads_bytes,
    uploads_count,
    counts_json,
) = sys.argv[1:11]

manifest = {
    "timestamp": timestamp,
    "database_file": db_file,
    "database_sha256": db_sha,
    "database_bytes": int(db_bytes),
    "uploads_file": uploads_file,
    "uploads_sha256": uploads_sha,
    "uploads_bytes": int(uploads_bytes),
    "uploads_file_count": int(uploads_count),
    "counts": json.loads(counts_json),
}

with open(manifest_path, "w", encoding="utf-8") as handle:
    json.dump(manifest, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY

find "$BACKUP_DIR" -type f -mtime +"$RETENTION_DAYS" -delete

echo "Backup OK:"
echo "  dump:     $BACKUP_DIR/$db_file"
echo "  uploads:  $BACKUP_DIR/$uploads_file"
echo "  manifest: $BACKUP_DIR/$manifest_file"
