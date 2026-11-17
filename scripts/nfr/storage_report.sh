#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT_DIR"

mkdir -p reports/nfr

set +e
docker compose exec -T backend python -m app.core.storage_report "$@" \
    > reports/nfr/storage.json
status=$?
set -e

cat reports/nfr/storage.json
exit "$status"
