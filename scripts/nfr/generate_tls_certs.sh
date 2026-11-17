#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
CERT_DIR="$ROOT_DIR/certs"

mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$CERT_DIR/localhost.key" \
    -out "$CERT_DIR/localhost.crt" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
    >/dev/null

chmod 600 "$CERT_DIR/localhost.key"
chmod 644 "$CERT_DIR/localhost.crt"

echo "Certificados autofirmados generados en $CERT_DIR"
