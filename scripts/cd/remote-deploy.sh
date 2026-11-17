#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage: scripts/cd/remote-deploy.sh <user@host>

Or set SSH_USER and SSH_HOST instead of passing a host.

Environment:
  DEPLOY_PATH         Remote directory, relative to the remote home. Default: hito.
  DEMO_DOMAIN         Public demo domain. Default: hitoapp.ddns.net.
  DEMO_INTERNAL_PORT  Loopback port for the demo web container. Default: 9080.
  CERTBOT_EMAIL       Optional Let's Encrypt account email.
  ENABLE_HTTPS        Set to 0 to skip the Nginx/Let's Encrypt setup. Default: 1.
  SSH_PORT            SSH port. Default: 22.
EOF
    exit 0
fi

REMOTE="${1:-}"
if [[ -z "$REMOTE" ]]; then
    if [[ -n "${SSH_USER:-}" && -n "${SSH_HOST:-}" ]]; then
        REMOTE="${SSH_USER}@${SSH_HOST}"
    else
        printf 'Usage: scripts/cd/remote-deploy.sh <user@host>\n' >&2
        printf 'Or set SSH_USER and SSH_HOST.\n' >&2
        exit 2
    fi
fi

REMOTE_DIR="${DEPLOY_PATH:-hito}"
DEMO_DOMAIN="${DEMO_DOMAIN:-hitoapp.ddns.net}"
DEMO_INTERNAL_PORT="${DEMO_INTERNAL_PORT:-9080}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
ENABLE_HTTPS="${ENABLE_HTTPS:-1}"
SSH_PORT="${SSH_PORT:-}"

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "$1" >&2
        exit 1
    }
}

require_command ssh
require_command rsync

SSH_OPTS=()
RSYNC_SSH="ssh"
if [[ -n "$SSH_PORT" ]]; then
    SSH_OPTS=(-p "$SSH_PORT")
    RSYNC_SSH="ssh -p ${SSH_PORT}"
fi

printf 'Syncing working tree to %s:%s\n' "$REMOTE" "$REMOTE_DIR"
ssh "${SSH_OPTS[@]}" "$REMOTE" "mkdir -p '$REMOTE_DIR'"
rsync -az --delete -e "$RSYNC_SSH" \
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

printf 'Deploying demo on %s (internal port %s)\n' "$REMOTE" "$DEMO_INTERNAL_PORT"
ssh "${SSH_OPTS[@]}" "$REMOTE" \
    "cd '$REMOTE_DIR' && DEMO_DOMAIN='$DEMO_DOMAIN' DEMO_INTERNAL_PORT='$DEMO_INTERNAL_PORT' CERTBOT_EMAIL='$CERTBOT_EMAIL' ENABLE_HTTPS='$ENABLE_HTTPS' ./scripts/cd/deploy-demo.sh"

if [[ "$ENABLE_HTTPS" == "1" ]]; then
    printf 'Demo available at https://%s\n' "$DEMO_DOMAIN"
else
    printf 'Demo available at http://127.0.0.1:%s on the remote host\n' "$DEMO_INTERNAL_PORT"
fi
