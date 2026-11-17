#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT_DIR"

compose_tls() {
    docker compose -p hito_tls -f compose.yaml -f compose.tls.yaml "$@"
}

show_failure_logs() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "TLS smoke test failed with status $status" >&2
        compose_tls ps >&2 || true
        compose_tls logs --tail=80 db backend web >&2 || true
    fi
    exit "$status"
}
trap show_failure_logs EXIT

echo "==> Generating self-signed certificates"
./scripts/nfr/generate_tls_certs.sh

echo "==> Building and starting the TLS stack"
compose_tls up --build -d db backend web

echo "==> Waiting for HTTPS health check"
attempt=0
until curl -kfsS https://localhost:8443/health/ready >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        echo "The TLS stack did not become ready in 120 seconds." >&2
        exit 1
    fi
    sleep 2
done

echo "==> Seeding demo data"
compose_tls exec -T backend python -m app.seed

demo_password=$(compose_tls exec -T backend python -c '
from app.seed import DEMO_PASSWORD

print(DEMO_PASSWORD)
')

echo "==> Running TLS checks"
DEMO_PASSWORD="$demo_password" python3 scripts/nfr/tls_check.py \
    --host localhost \
    --https-port 8443 \
    --http-port 8081

echo "TLS smoke OK."

if [ "${TLS_CLEANUP:-0}" = "1" ]; then
    echo "==> Removing the TLS stack"
    compose_tls down -v
fi
