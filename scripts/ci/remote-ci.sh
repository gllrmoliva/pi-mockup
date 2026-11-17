#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

REMOTE=""
PROFILE="pr"
REMOTE_DIR="${REMOTE_DIR:-hito-ci}"
SYNC=1
FETCH=1
KEEP_ARG=""

usage() {
    cat <<'EOF'
Usage: scripts/ci/remote-ci.sh <user@host> [options]

Copies the working tree to a remote Linux host and runs scripts/ci/run-ci.sh there.

Options:
  --profile pr|nightly|all  CI profile. Default: pr.
  --remote-dir PATH         Remote directory, relative to the remote home.
                            Default: hito-ci.
  --no-sync                 Do not copy the repository before running.
  --no-fetch                Do not copy reports back after the run.
  --keep                    Keep CI containers and volumes on the remote host.
  -h, --help                Show this help.

Examples:
  scripts/ci/remote-ci.sh fgonzalez@hitoapp.ddns.net
  scripts/ci/remote-ci.sh fgonzalez@hitoapp.ddns.net --profile all
  REMOTE_DIR=/opt/hito-ci scripts/ci/remote-ci.sh fgonzalez@hitoapp.ddns.net
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            PROFILE="${2:-}"
            shift 2
            ;;
        --remote-dir)
            REMOTE_DIR="${2:-}"
            shift 2
            ;;
        --no-sync)
            SYNC=0
            shift
            ;;
        --no-fetch)
            FETCH=0
            shift
            ;;
        --keep)
            KEEP_ARG="--keep"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            printf 'Unknown option: %s\n\n' "$1" >&2
            usage >&2
            exit 2
            ;;
        *)
            if [[ -n "$REMOTE" ]]; then
                printf 'Unexpected argument: %s\n\n' "$1" >&2
                usage >&2
                exit 2
            fi
            REMOTE="$1"
            shift
            ;;
    esac
done

if [[ -z "$REMOTE" ]]; then
    usage >&2
    exit 2
fi

case "$PROFILE" in
    pr|nightly|all) ;;
    *)
        printf 'Invalid profile: %s\n' "$PROFILE" >&2
        exit 2
        ;;
esac

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "$1" >&2
        exit 1
    }
}

require_command ssh
if [[ "$SYNC" -eq 1 || "$FETCH" -eq 1 ]]; then
    require_command rsync
fi

if [[ "$SYNC" -eq 1 ]]; then
    printf 'Syncing working tree to %s:%s\n' "$REMOTE" "$REMOTE_DIR"
    ssh "$REMOTE" "mkdir -p '$REMOTE_DIR'"
    rsync -az --delete \
        --include='.env.example' \
        --exclude='.env*' \
        --exclude='.git/' \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='.pytest_cache/' \
        --exclude='.ruff_cache/' \
        --exclude='node_modules/' \
        --exclude='frontend/node_modules/' \
        --exclude='frontend/dist/' \
        --exclude='frontend/test-results/' \
        --exclude='reports/' \
        --exclude='backups/' \
        --exclude='certs/' \
        --exclude='proxy/' \
        "$ROOT_DIR/" "$REMOTE:$REMOTE_DIR/"
fi

set +e
ssh "$REMOTE" "cd '$REMOTE_DIR' && ./scripts/ci/run-ci.sh --profile '$PROFILE' $KEEP_ARG"
status=$?
set -e

if [[ "$FETCH" -eq 1 ]]; then
    printf 'Fetching reports from %s:%s/reports/ci\n' "$REMOTE" "$REMOTE_DIR"
    mkdir -p "$ROOT_DIR/reports/ci"
    rsync -az "$REMOTE:$REMOTE_DIR/reports/ci/" "$ROOT_DIR/reports/ci/" || true
fi

exit "$status"
