#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT_DIR"

mkdir -p reports/nfr/coverage

docker compose --profile test run --rm --build \
    --volume "$ROOT_DIR/reports:/app/reports" \
    --entrypoint /bin/sh \
    backend-test -c '
        alembic upgrade head &&
        pytest \
            --cov-config=/app/pyproject.toml \
            --cov=app.modules.auth.security \
            --cov=app.modules.auth.service \
            --cov=app.modules.deliverables.dependencies \
            --cov=app.modules.deliverables.service \
            --cov=app.modules.projects.dependencies \
            --cov=app.modules.projects.service \
            --cov=app.modules.storage.service \
            --cov=app.api.deps \
            --cov=app.core.errors \
            --cov=app.core.audit.service \
            --cov-report=term-missing \
            --cov-report=xml:/app/reports/nfr/coverage/coverage.xml \
            --cov-report=html:/app/reports/nfr/coverage/html \
            --cov-fail-under=80
    '
