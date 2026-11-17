#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage: scripts/cd/deploy-demo.sh

Builds the demo stack, creates .env.demo if missing, runs migrations by
starting the backend, seeds demo data, verifies demo login and configures
the Nginx HTTPS proxy by default.

Environment:
  DEMO_DOMAIN         Public domain. Default: hitoapp.ddns.net.
  DEMO_INTERNAL_PORT  Loopback port for the demo web container. Default: 9080.
  ENABLE_HTTPS        Set to 0 to skip the Nginx/Let's Encrypt setup. Default: 1.
  CERTBOT_EMAIL       Optional Let's Encrypt account email.
EOF
    exit 0
fi

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

DEMO_DOMAIN="${DEMO_DOMAIN:-hitoapp.ddns.net}"
DEMO_INTERNAL_PORT="${DEMO_INTERNAL_PORT:-9080}"
ENABLE_HTTPS="${ENABLE_HTTPS:-1}"
export DEMO_DOMAIN DEMO_INTERNAL_PORT
ENV_FILE="$ROOT_DIR/.env.demo"

compose_demo() {
    docker compose --env-file "$ENV_FILE" \
        -f "$ROOT_DIR/compose.yaml" \
        -f "$ROOT_DIR/compose.demo.yaml" "$@"
}

base_url="http://127.0.0.1:${DEMO_INTERNAL_PORT}"

show_failure_logs() {
    local status=$?
    if [[ "$status" -ne 0 ]]; then
        printf 'Demo deployment failed with status %s.\n' "$status" >&2
        compose_demo ps >&2 || true
        compose_demo logs --tail=100 backend web >&2 || true
        if [[ "$ENABLE_HTTPS" == "1" ]]; then
            docker compose -f "$ROOT_DIR/compose.proxy.yaml" ps >&2 || true
            docker compose -f "$ROOT_DIR/compose.proxy.yaml" logs --tail=100 nginx >&2 || true
        fi
    fi
    exit "$status"
}
trap show_failure_logs EXIT

set_env_value() {
    local key=$1
    local value=$2
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
    fi
}

if [[ ! -f "$ENV_FILE" ]]; then
    if ! command -v openssl >/dev/null 2>&1; then
        printf 'openssl is required to generate the demo database password.\n' >&2
        exit 1
    fi

    umask 077
    database_password="$(openssl rand -hex 24)"
    cat > "$ENV_FILE" <<EOF
APP_NAME=Hito
APP_VERSION=0.1.0
APP_ENV=demo
LOG_LEVEL=INFO
SESSION_COOKIE_SECURE=false
SESSION_TTL_HOURS=8
MAX_FAILED_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15
TRUST_PROXY_HEADERS=false
POSTGRES_DB=hito
POSTGRES_USER=hito
POSTGRES_PASSWORD=${database_password}
EOF
    printf 'Created %s with a generated database password.\n' "$ENV_FILE"
else
    printf 'Keeping existing %s.\n' "$ENV_FILE"
fi

if [[ "$ENABLE_HTTPS" == "1" ]]; then
    secure_cookie=true
    trust_proxy=true
else
    secure_cookie=false
    trust_proxy=false
fi
set_env_value APP_ENV demo
set_env_value SESSION_COOKIE_SECURE "$secure_cookie"
set_env_value TRUST_PROXY_HEADERS "$trust_proxy"
chmod 600 "$ENV_FILE"

printf '==> Validating demo Compose configuration\n'
compose_demo config >/dev/null

printf '==> Building and starting the demo stack\n'
compose_demo up --build -d

printf '==> Waiting for the demo health check\n'
attempt=0
until curl -fsS "${base_url}/health/ready" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [[ "$attempt" -ge 60 ]]; then
        printf 'The demo stack did not become ready.\n' >&2
        exit 1
    fi
    sleep 2
done

printf '==> Seeding demo data\n'
compose_demo exec -T backend python -m app.seed

printf '==> Checking demo login\n'
demo_password="$(
    compose_demo exec -T backend python -c \
        'from app.seed import DEMO_PASSWORD; print(DEMO_PASSWORD)'
)"
login_payload="$(
    compose_demo exec -T backend python -c \
        'import json; from app.seed import DEMO_PASSWORD; print(json.dumps({"email": "camila.soto@udec.cl", "password": DEMO_PASSWORD}))'
)"
login_response="$(
    curl -fsS -X POST "${base_url}/api/v1/auth/login" \
        -H 'Content-Type: application/json' \
        -d "$login_payload"
)"
printf '%s' "$login_response" | grep -q 'camila.soto@udec.cl'

if [[ "$ENABLE_HTTPS" == "1" ]]; then
    printf '==> Configuring the Nginx HTTPS proxy\n'
    DEMO_DOMAIN="$DEMO_DOMAIN" \
        CERTBOT_EMAIL="${CERTBOT_EMAIL:-}" \
        "$ROOT_DIR/scripts/cd/setup-nginx-tls.sh"
    public_url="https://${DEMO_DOMAIN}"
else
    public_url="http://127.0.0.1:${DEMO_INTERNAL_PORT}"
fi

printf '\nDemo deployment ready.\n'
printf 'URL: %s\n' "$public_url"
printf 'Demo user: camila.soto@udec.cl / %s\n' "$demo_password"
if [[ "$ENABLE_HTTPS" == "1" ]]; then
    printf 'HTTP is redirected to HTTPS and the session cookie is Secure.\n'
else
    printf 'HTTPS was disabled with ENABLE_HTTPS=0.\n'
fi
