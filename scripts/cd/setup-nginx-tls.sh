#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage: scripts/cd/setup-nginx-tls.sh

Starts the Nginx proxy on ports 80/443, obtains or reuses a Let's Encrypt
certificate and enables the HTTP-to-HTTPS redirect.

Environment:
  DEMO_DOMAIN    Public domain. Default: hitoapp.ddns.net.
  CERTBOT_EMAIL  Optional Let's Encrypt account email.
EOF
    exit 0
fi

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

DOMAIN="${DEMO_DOMAIN:-hitoapp.ddns.net}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
PROXY_DIR="$ROOT_DIR/proxy"
CONF_DIR="$PROXY_DIR/conf.d"
CERTBOT_CONF="$PROXY_DIR/certbot/conf"
CERTBOT_WWW="$PROXY_DIR/certbot/www"

mkdir -p "$CONF_DIR" "$CERTBOT_CONF" "$CERTBOT_WWW"

if ! docker network inspect hito_default >/dev/null 2>&1; then
    printf 'Docker network hito_default is missing. Start the demo stack first.\n' >&2
    exit 1
fi

compose_proxy() {
    docker compose -f "$ROOT_DIR/compose.proxy.yaml" "$@"
}

render_config() {
    local template=$1
    sed \
        -e "s|__DOMAIN__|$DOMAIN|g" \
        "$ROOT_DIR/deploy/nginx/$template" \
        > "$CONF_DIR/hito.conf"
    chmod 644 "$CONF_DIR/hito.conf"
}

certificate_exists() {
    # El certificado es propiedad de root; se comprueba dentro de un contenedor.
    compose_proxy run --rm --no-deps --entrypoint sh certbot \
        -c "test -f /etc/letsencrypt/live/${DOMAIN}/fullchain.pem" \
        >/dev/null 2>&1
}

wait_for_http() {
    local attempt
    for attempt in $(seq 1 30); do
        if curl -sS --noproxy '*' -o /dev/null "http://127.0.0.1/" 2>/dev/null; then
            return 0
        fi
        sleep 1
    done
    return 1
}

if certificate_exists; then
    printf '==> Existing TLS certificate found for %s\n' "$DOMAIN"
    render_config https.conf.template
    compose_proxy up -d nginx
    if ! compose_proxy exec -T nginx nginx -s reload >/dev/null 2>&1; then
        compose_proxy restart nginx >/dev/null
    fi
else
    printf '==> Starting HTTP-only Nginx for the ACME challenge\n'
    render_config http-only.conf.template
    compose_proxy up -d nginx

    if ! wait_for_http; then
        printf 'Nginx did not become available on port 80.\n' >&2
        exit 1
    fi

    certbot_args=(
        certonly
        --webroot
        -w /var/www/certbot
        -d "$DOMAIN"
        --agree-tos
        --no-eff-email
        --non-interactive
    )
    if [[ -n "$CERTBOT_EMAIL" ]]; then
        certbot_args+=(--email "$CERTBOT_EMAIL")
    else
        certbot_args+=(--register-unsafely-without-email)
    fi

    printf '==> Requesting a Let’s Encrypt certificate for %s\n' "$DOMAIN"
    compose_proxy run --rm certbot "${certbot_args[@]}"

    if ! certificate_exists; then
        printf 'Certificate was not created for %s.\n' "$DOMAIN" >&2
        exit 1
    fi

    printf '==> Enabling HTTPS and redirecting HTTP\n'
    render_config https.conf.template
    if ! compose_proxy exec -T nginx nginx -s reload >/dev/null 2>&1; then
        compose_proxy restart nginx >/dev/null
    fi
fi

printf '==> Verifying HTTPS locally\n'
if ! curl -fsS --noproxy '*' --max-time 20 \
    --resolve "$DOMAIN:443:127.0.0.1" \
    "https://$DOMAIN/health/ready" >/dev/null; then
    printf 'HTTPS verification failed for https://%s.\n' "$DOMAIN" >&2
    compose_proxy logs --tail=50 nginx >&2 || true
    exit 1
fi

printf 'HTTPS ready: https://%s\n' "$DOMAIN"
