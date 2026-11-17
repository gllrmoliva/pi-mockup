#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage: scripts/cd/renew-certificates.sh [--dry-run]

Renews the Let's Encrypt certificate for the demo domain and reloads Nginx.
Use --dry-run to validate the renewal against the Let's Encrypt staging
environment without changing the installed certificate.

Environment:
  DEMO_DOMAIN  Public domain. Default: hitoapp.ddns.net.
EOF
    exit 0
fi

DRY_RUN=0
case "${1:-}" in
    "")
        ;;
    --dry-run)
        DRY_RUN=1
        ;;
    *)
        printf 'Unknown option: %s\n' "$1" >&2
        printf 'Run scripts/cd/renew-certificates.sh --help for usage.\n' >&2
        exit 2
        ;;
esac

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

DOMAIN="${DEMO_DOMAIN:-hitoapp.ddns.net}"

if ! docker network inspect hito_default >/dev/null 2>&1; then
    printf 'Docker network hito_default is missing. Start the demo stack first.\n' >&2
    exit 1
fi

compose_proxy() {
    docker compose -f "$ROOT_DIR/compose.proxy.yaml" "$@"
}

certbot_args=(
    renew
    --webroot
    -w /var/www/certbot
    --quiet
)
if [[ "$DRY_RUN" == "1" ]]; then
    certbot_args+=(--dry-run)
    printf '==> Validating certificate renewal for %s (dry run)\n' "$DOMAIN"
else
    printf '==> Renewing certificate for %s if needed\n' "$DOMAIN"
fi

compose_proxy run --rm certbot "${certbot_args[@]}"

if [[ "$DRY_RUN" == "0" ]]; then
    printf '==> Reloading Nginx\n'
    compose_proxy exec -T nginx nginx -s reload
fi

printf 'Certificate renewal check finished for %s.\n' "$DOMAIN"
