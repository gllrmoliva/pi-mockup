#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PROFILE="pr"
KEEP=0
SKIP_PORT_CHECK=0
PROJECT_NAME="${CI_PROJECT_NAME:-hito_ci}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_ROOT="${CI_REPORT_DIR:-$ROOT_DIR/reports/ci}"
REPORT_DIR="$REPORT_ROOT/$RUN_ID"
LOG_FILE="$REPORT_DIR/run.log"

usage() {
    cat <<'EOF'
Usage: scripts/ci/run-ci.sh [options]

Runs the repository CI on the current Linux host.

Options:
  --profile pr|nightly|all  CI profile to run. Default: pr.
  --keep                    Keep CI containers and volumes after the run.
  --skip-port-check         Do not fail when CI ports are already in use.
  -h, --help                Show this help.

Environment:
  CI_PROJECT_NAME   Compose project for the main CI stack. Default: hito_ci.
                    It must not be "hito" (the production project name).
  CI_REPORT_DIR     Root directory for reports. Default: reports/ci.
  CI_LOCK_FILE      Lock file. Default: /tmp/hito-ci.lock.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            PROFILE="${2:-}"
            shift 2
            ;;
        --keep)
            KEEP=1
            shift
            ;;
        --skip-port-check)
            SKIP_PORT_CHECK=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$PROFILE" in
    pr|nightly|all) ;;
    *)
        printf 'Invalid profile: %s\n' "$PROFILE" >&2
        usage >&2
        exit 2
        ;;
esac

if [[ "$PROJECT_NAME" == "hito" ]]; then
    printf 'CI_PROJECT_NAME must not be "hito": that is the production project.\n' >&2
    exit 2
fi

mkdir -p "$REPORT_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
export CI=true
export APP_NAME=Hito
export APP_VERSION=0.1.0
export APP_ENV=test
export LOG_LEVEL=WARNING
export SESSION_COOKIE_SECURE=false
export TRUST_PROXY_HEADERS=false
export POSTGRES_DB=hito
export POSTGRES_USER=hito
export POSTGRES_PASSWORD="${CI_POSTGRES_PASSWORD:-hito-ci-change-me}"

LOCK_FILE="${CI_LOCK_FILE:-/tmp/hito-ci.lock}"
if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
        printf 'Another CI run is already using %s.\n' "$LOCK_FILE" >&2
        exit 75
    fi
fi

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

load_nvm() {
    if [[ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]]; then
        set +u
        # shellcheck disable=SC1090
        . "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
        set -u
    fi
}

prepare_node() {
    load_nvm
    if command -v nvm >/dev/null 2>&1; then
        nvm use 22 >/dev/null 2>&1 || true
    fi

    require_command node
    require_command npm

    local node_major
    node_major="$(node -p 'process.versions.node.split(".")[0]')"
    [[ "$node_major" == "22" ]] || fail "Node 22 is required; found $(node --version)."
}

check_tools() {
    require_command docker
    require_command python3
    require_command curl
    require_command tee

    docker info >/dev/null 2>&1 || fail "Docker daemon is not available."
    docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."

    python3 - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required.")
PY

    prepare_node

    docker compose -p "$PROJECT_NAME" -f "$ROOT_DIR/compose.yaml" config \
        >/dev/null 2>&1 || fail "compose.yaml is not valid for the installed Compose version."
    docker compose -p hito_e2e -f "$ROOT_DIR/compose.yaml" \
        -f "$ROOT_DIR/compose.e2e.yaml" config \
        >/dev/null 2>&1 || fail "compose.e2e.yaml is not valid for the installed Compose version."
    docker compose -p hito_tls -f "$ROOT_DIR/compose.yaml" \
        -f "$ROOT_DIR/compose.tls.yaml" config \
        >/dev/null 2>&1 || fail "compose.tls.yaml is not valid for the installed Compose version."
    if [[ "$PROFILE" != "pr" ]]; then
        docker compose -p hito_perf -f "$ROOT_DIR/compose.yaml" \
            -f "$ROOT_DIR/compose.perf.yaml" config \
            >/dev/null 2>&1 || fail "compose.perf.yaml is not valid for the installed Compose version."
    fi
}

compose_ci() {
    docker compose -p "$PROJECT_NAME" -f "$ROOT_DIR/compose.yaml" "$@"
}

cleanup_stack() {
    compose_ci down -v >/dev/null 2>&1 || true
    docker compose -p hito_e2e -f "$ROOT_DIR/compose.yaml" \
        -f "$ROOT_DIR/compose.e2e.yaml" down -v >/dev/null 2>&1 || true
    docker compose -p hito_tls -f "$ROOT_DIR/compose.yaml" \
        -f "$ROOT_DIR/compose.tls.yaml" down -v >/dev/null 2>&1 || true
    if [[ "$PROFILE" != "pr" ]]; then
        docker compose -p hito_perf -f "$ROOT_DIR/compose.yaml" \
            -f "$ROOT_DIR/compose.perf.yaml" down -v >/dev/null 2>&1 || true
    fi
}

copy_artifacts() {
    mkdir -p "$REPORT_DIR/nfr"
    if [[ -d "$ROOT_DIR/reports/nfr" ]]; then
        cp -a "$ROOT_DIR/reports/nfr/." "$REPORT_DIR/nfr/" 2>/dev/null || true
    fi

    mkdir -p "$REPORT_DIR/backups"
    if compgen -G "$ROOT_DIR/backups/manifest-*.json" >/dev/null; then
        cp "$ROOT_DIR/backups/manifest-"*.json "$REPORT_DIR/backups/" 2>/dev/null || true
    fi
}

finish() {
    local status=$?
    trap - EXIT

    copy_artifacts

    if [[ "$KEEP" -eq 0 ]]; then
        cleanup_stack
    fi

    if [[ "$status" -eq 0 ]]; then
        printf '\nCI passed. Reports: %s\n' "$REPORT_DIR"
    else
        printf '\nCI failed with status %s. Reports: %s\n' "$status" "$REPORT_DIR" >&2
    fi

    exit "$status"
}
trap finish EXIT

port_in_use() {
    local port=$1
    ss -ltn 2>/dev/null | awk -v pattern=":${port}" \
        '$4 ~ pattern { found = 1 } END { exit(found ? 0 : 1) }'
}

check_ports() {
    [[ "$SKIP_PORT_CHECK" -eq 1 ]] && return 0

    if ! command -v ss >/dev/null 2>&1; then
        printf 'WARNING: ss is not available; skipping port checks.\n' >&2
        return 0
    fi

    local ports=(8000 18080 8081 8443)
    if [[ "$PROFILE" == "pr" || "$PROFILE" == "all" ]]; then
        ports+=(8080)
    fi
    if [[ "$PROFILE" != "pr" ]]; then
        ports+=(18081)
    fi

    local port
    for port in "${ports[@]}"; do
        if port_in_use "$port"; then
            fail "Port $port is already in use. Stop the conflicting service or use --skip-port-check."
        fi
    done
}

run_step() {
    local label=$1
    shift
    printf '\n==> %s\n' "$label"
    "$@"
}

backend_quality() {
    compose_ci --profile test run --rm --build --entrypoint /bin/sh \
        backend-test -c \
        "ruff check app tests alembic && ruff format --check app tests alembic && pyright"
}

backend_coverage() {
    "$ROOT_DIR/scripts/nfr/coverage.sh"
}

prepare_frontend() {
    (cd "$ROOT_DIR/frontend" && npm ci)
}

frontend_quality() {
    (cd "$ROOT_DIR/frontend" && npm run lint && npm run typecheck && npm run test:run && npm run build)
}

docker_smoke() {
    SMOKE_CLEANUP=1 "$ROOT_DIR/scripts/nfr/compose_smoke.sh"
}

chromium_e2e() {
    (cd "$ROOT_DIR/frontend" && npx playwright install chromium)
    E2E_CLEANUP=1 "$ROOT_DIR/scripts/nfr/e2e.sh" --project=chromium
}

tls_handshake() {
    TLS_CLEANUP=1 "$ROOT_DIR/scripts/nfr/tls_smoke.sh"
}

start_ci_backend() {
    compose_ci up -d --build db backend

    local attempt
    for attempt in $(seq 1 60); do
        if curl -fsS http://localhost:8000/health/ready >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done

    fail "The CI backend did not become ready."
}

seed_ci() {
    compose_ci exec -T backend python -m app.seed
}

backup_restore() {
    start_ci_backend
    seed_ci
    "$ROOT_DIR/scripts/nfr/backup.sh"
    "$ROOT_DIR/scripts/nfr/restore_drill.sh"
}

storage_report() {
    start_ci_backend
    seed_ci
    "$ROOT_DIR/scripts/nfr/storage_report.sh"
}

all_browser_e2e() {
    (cd "$ROOT_DIR/frontend" && npx playwright install chromium firefox webkit)
    E2E_CLEANUP=1 "$ROOT_DIR/scripts/nfr/e2e.sh"
}

performance_report() {
    (cd "$ROOT_DIR/frontend" && npx playwright install chromium)
    PERF_USERS=100 \
        PERF_DURATION=900 \
        PERF_RAMP_UP=30 \
        PERF_PROFESSORS=30 \
        PERF_ENFORCE=0 \
        PERF_CLEANUP=1 \
        "$ROOT_DIR/scripts/nfr/perf.sh"
}

printf 'CI profile: %s\n' "$PROFILE"
printf 'Compose project: %s\n' "$PROJECT_NAME"
printf 'Reports: %s\n' "$REPORT_DIR"

run_step "Preflight checks" check_tools
run_step "Reset previous CI stacks" cleanup_stack
run_step "Port checks" check_ports

if [[ "$PROFILE" == "pr" || "$PROFILE" == "all" ]]; then
    run_step "Backend quality" backend_quality
    run_step "Backend tests and coverage gate" backend_coverage
    run_step "Install frontend dependencies" prepare_frontend
    run_step "Frontend quality" frontend_quality
    run_step "Docker Compose smoke" docker_smoke
    run_step "Chromium E2E" chromium_e2e
    run_step "TLS handshake" tls_handshake
fi

if [[ "$PROFILE" == "nightly" || "$PROFILE" == "all" ]]; then
    if [[ "$PROFILE" == "nightly" ]]; then
        run_step "Install frontend dependencies" prepare_frontend
    fi
    run_step "Backup and restore drill" backup_restore
    run_step "Storage report" storage_report
    run_step "All-browser E2E" all_browser_e2e
    run_step "Performance report" performance_report
fi
