#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT_DIR"

BACKUP_DIR=${BACKUP_DIR:-"$ROOT_DIR/backups"}
REPORT_DIR=${REPORT_DIR:-"$ROOT_DIR/reports/nfr"}
RPO_HOURS=${RPO_HOURS:-24}
RTO_HOURS=${RTO_HOURS:-4}
mkdir -p "$REPORT_DIR"

latest_manifest=$(ls -1t "$BACKUP_DIR"/manifest-*.json 2>/dev/null | head -n 1 || true)
if [ -z "$latest_manifest" ]; then
    echo "No backup manifest found in $BACKUP_DIR. Run backup.sh first." >&2
    exit 1
fi

manifest_values=$(python3 - "$latest_manifest" <<'PY'
import json
import shlex
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)

for key in (
    "database_file",
    "database_sha256",
    "uploads_file",
    "uploads_sha256",
    "uploads_file_count",
):
    print(f"{key.upper()}={shlex.quote(str(data[key]))}")

print("COUNTS_JSON=" + shlex.quote(json.dumps(data["counts"])))
PY
)
eval "$manifest_values"

database_path="$BACKUP_DIR/$DATABASE_FILE"
uploads_path="$BACKUP_DIR/$UPLOADS_FILE"
[ -f "$database_path" ] || {
    echo "Missing database backup: $database_path" >&2
    exit 1
}
[ -f "$uploads_path" ] || {
    echo "Missing uploads backup: $uploads_path" >&2
    exit 1
}

verify_sha() {
    file=$1
    expected=$2
    label=$3
    actual=$(sha256sum "$file" | cut -d' ' -f1)
    if [ "$actual" != "$expected" ]; then
        echo "SHA-256 mismatch for $label." >&2
        exit 1
    fi
}

echo "==> Verifying backup hashes"
verify_sha "$database_path" "$DATABASE_SHA256" "database"
verify_sha "$uploads_path" "$UPLOADS_SHA256" "uploads"

now=$(date +%s)
manifest_mtime=$(stat -c %Y "$latest_manifest")
age_seconds=$((now - manifest_mtime))
age_hours=$((age_seconds / 3600))
if [ "$age_seconds" -le $((RPO_HOURS * 3600)) ]; then
    rpo_ok=true
else
    rpo_ok=false
    echo "Backup is older than the RPO of ${RPO_HOURS} hours." >&2
fi

DRILL_NAME="hito-restore-drill-$$"
TMP_UPLOADS=$(mktemp -d)
cleanup() {
    docker rm -f "$DRILL_NAME" >/dev/null 2>&1 || true
    rm -rf "$TMP_UPLOADS"
}
trap cleanup EXIT

echo "==> Starting throwaway PostgreSQL"
docker run -d --name "$DRILL_NAME" \
    -e POSTGRES_PASSWORD=drill \
    -e POSTGRES_USER=drill \
    -e POSTGRES_DB=drill \
    postgres:18-alpine >/dev/null

attempt=0
until docker exec "$DRILL_NAME" pg_isready -U drill -d drill >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        echo "The throwaway database did not become ready." >&2
        exit 1
    fi
    sleep 1
done

start=$(date +%s)

echo "==> Restoring PostgreSQL"
docker exec -i -e PGPASSWORD=drill "$DRILL_NAME" \
    pg_restore -U drill -d drill --no-owner --no-privileges < "$database_path"

counts_ok=true
for table in usuario proyecto participacion hito entregable entrega archivo revision comentario; do
    expected=$(python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["counts"][sys.argv[2]])' \
        "$latest_manifest" "$table")
    actual=$(docker exec -e PGPASSWORD=drill "$DRILL_NAME" \
        psql -U drill -d drill -Atc "SELECT count(*) FROM $table" \
        | tr -d '[:space:]')
    if [ "$expected" != "$actual" ]; then
        echo "Row count mismatch in $table: expected $expected, got $actual." >&2
        counts_ok=false
    fi
done

echo "==> Restoring uploads"
tar --sparse -xzf "$uploads_path" -C "$TMP_UPLOADS"
restored_files=$(find "$TMP_UPLOADS" -type f | wc -l | tr -d '[:space:]')
uploads_ok=true
if [ "$restored_files" -ne "$UPLOADS_FILE_COUNT" ]; then
    echo "Uploads count mismatch: expected $UPLOADS_FILE_COUNT, got $restored_files." >&2
    uploads_ok=false
fi

end=$(date +%s)
rto_seconds=$((end - start))
rto_hours=$((rto_seconds / 3600))
if [ "$rto_seconds" -le $((RTO_HOURS * 3600)) ]; then
    rto_ok=true
else
    rto_ok=false
    echo "Restore exceeded the RTO of ${RTO_HOURS} hours." >&2
fi

status=pass
if [ "$rpo_ok" != true ] || [ "$counts_ok" != true ] || \
    [ "$uploads_ok" != true ] || [ "$rto_ok" != true ]; then
    status=fail
fi

python3 - \
    "$REPORT_DIR/restore-drill.json" \
    "$latest_manifest" \
    "$age_hours" \
    "$RPO_HOURS" \
    "$rpo_ok" \
    "$rto_seconds" \
    "$RTO_HOURS" \
    "$rto_ok" \
    "$counts_ok" \
    "$uploads_ok" \
    "$restored_files" \
    "$UPLOADS_FILE_COUNT" \
    "$status" <<'PY'
import json
import sys
from datetime import UTC, datetime

(
    report_path,
    manifest,
    age_hours,
    rpo_hours,
    rpo_ok,
    rto_seconds,
    rto_hours,
    rto_ok,
    counts_ok,
    uploads_ok,
    restored_files,
    expected_files,
    status,
) = sys.argv[1:14]

report = {
    "timestamp": datetime.now(UTC).isoformat(),
    "backup_manifest": manifest,
    "backup_age_hours": int(age_hours),
    "rpo_hours": int(rpo_hours),
    "rpo_ok": rpo_ok == "true",
    "rto_seconds": int(rto_seconds),
    "rto_hours": int(rto_hours),
    "rto_ok": rto_ok == "true",
    "counts_ok": counts_ok == "true",
    "uploads_ok": uploads_ok == "true",
    "restored_uploads_files": int(restored_files),
    "expected_uploads_files": int(expected_files),
    "status": status,
}

with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY

echo "Restore drill report: $REPORT_DIR/restore-drill.json"
echo "RPO: ${age_hours}h (ok=$rpo_ok); RTO: ${rto_seconds}s (ok=$rto_ok); status=$status"

if [ "$status" != "pass" ]; then
    exit 1
fi
