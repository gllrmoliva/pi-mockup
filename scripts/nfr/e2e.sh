#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT_DIR"

compose_e2e() {
    docker compose \
        -p hito_e2e \
        -f "$ROOT_DIR/compose.yaml" \
        -f "$ROOT_DIR/compose.e2e.yaml" \
        "$@"
}

show_failure_logs() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "E2E run failed with status $status" >&2
        compose_e2e ps >&2 || true
        compose_e2e logs --tail=80 db backend web >&2 || true
    fi
    exit "$status"
}
trap show_failure_logs EXIT

echo "==> Resetting the E2E stack"
compose_e2e down -v >/dev/null 2>&1 || true

echo "==> Building and starting db, backend and web"
compose_e2e up --build -d db backend web

echo "==> Waiting for the E2E stack"
attempt=0
until curl -fsS http://localhost:18080/health/ready >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        echo "The E2E stack did not become ready in 120 seconds." >&2
        exit 1
    fi
    sleep 2
done

echo "==> Seeding E2E data"
compose_e2e exec -T backend python -m app.seed

demo_password=$(compose_e2e exec -T backend python -c '
from app.seed import DEMO_PASSWORD

print(DEMO_PASSWORD)
')

echo "==> Running Playwright"
cd frontend
E2E_BASE_URL=http://localhost:18080 \
    E2E_DEMO_PASSWORD="$demo_password" \
    npx playwright test "$@"

if [ "${E2E_CLEANUP:-0}" = "1" ]; then
    echo "==> Removing the E2E stack"
    compose_e2e down -v
fi
