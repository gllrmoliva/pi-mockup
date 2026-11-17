#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT_DIR"

show_failure_logs() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "Smoke test failed with status $status" >&2
        docker compose ps >&2 || true
        docker compose logs --tail=80 db backend web >&2 || true
    fi
    exit "$status"
}
trap show_failure_logs EXIT

echo "==> Validating Compose configuration"
docker compose config >/dev/null

echo "==> Building and starting db, backend and web"
docker compose up --build -d db backend web

echo "==> Waiting for the full stack health check"
attempt=0
until curl -fsS http://localhost:8080/health/ready >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        echo "The stack did not become ready in 120 seconds." >&2
        exit 1
    fi
    sleep 2
done

echo "==> Seeding demo data"
docker compose exec -T backend python -m app.seed

echo "==> Checking the SPA entry point"
curl -fsS http://localhost:8080/ | grep -q '<div id="root">'

echo "==> Checking demo login"
login_payload=$(docker compose exec -T backend python -c '
import json
from app.seed import DEMO_PASSWORD

print(json.dumps({"email": "camila.soto@udec.cl", "password": DEMO_PASSWORD}))
')
response=$(curl -fsS -X POST http://localhost:8080/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d "$login_payload")
echo "$response" | grep -q 'camila.soto@udec.cl'

echo "Smoke OK: database, backend, web, seed and login."

if [ "${SMOKE_CLEANUP:-0}" = "1" ]; then
    echo "==> Removing the smoke stack"
    docker compose down -v
fi
