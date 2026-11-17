#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT_DIR"

PERF_USERS=${PERF_USERS:-100}
PERF_DURATION=${PERF_DURATION:-900}
PERF_RAMP_UP=${PERF_RAMP_UP:-30}
PERF_PROFESSORS=${PERF_PROFESSORS:-30}
PERF_ENFORCE=${PERF_ENFORCE:-0}
PERF_CLEANUP=${PERF_CLEANUP:-0}
SAMPLER_PID=""

compose_perf() {
    docker compose \
        -p hito_perf \
        -f "$ROOT_DIR/compose.yaml" \
        -f "$ROOT_DIR/compose.perf.yaml" \
        "$@"
}

stop_sampler() {
    if [ -n "$SAMPLER_PID" ] && kill -0 "$SAMPLER_PID" 2>/dev/null; then
        kill -TERM "$SAMPLER_PID" 2>/dev/null || true
        wait "$SAMPLER_PID" 2>/dev/null || true
    fi
    SAMPLER_PID=""
}

cleanup() {
    status=$?
    stop_sampler
    if [ "$status" -ne 0 ]; then
        echo "Performance run failed with status $status" >&2
        compose_perf ps >&2 || true
        compose_perf logs --tail=80 db backend web >&2 || true
    fi
    exit "$status"
}
trap cleanup EXIT

echo "==> Resetting the performance stack"
compose_perf down -v >/dev/null 2>&1 || true

echo "==> Building and starting db, backend and web"
compose_perf up --build -d db backend web

echo "==> Waiting for the performance stack"
attempt=0
until curl -fsS http://localhost:18081/health/ready >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 120 ]; then
        echo "The performance stack did not become ready." >&2
        exit 1
    fi
    sleep 2
done

echo "==> Seeding the SRS-scale dataset"
compose_perf exec -T backend python -m app.seed_perf

password=$(compose_perf exec -T backend python -c '
from app.seed_perf import PERF_PASSWORD

print(PERF_PASSWORD)
')

mkdir -p reports/nfr
: > reports/nfr/memory-samples.jsonl

echo "==> Sampling container memory"
python3 scripts/nfr/memory_sampler.py \
    > reports/nfr/memory-samples.jsonl \
    2> reports/nfr/memory-sampler.err &
SAMPLER_PID=$!

echo "==> Running API load test"
enforce_flag=""
if [ "$PERF_ENFORCE" = "1" ]; then
    enforce_flag="--enforce"
fi
docker compose \
    -p hito_perf \
    -f "$ROOT_DIR/compose.yaml" \
    -f "$ROOT_DIR/compose.perf.yaml" \
    run --rm --build \
    -e PERF_PASSWORD="$password" \
    --volume "$ROOT_DIR/scripts:/app/scripts:ro" \
    --volume "$ROOT_DIR/reports:/app/reports" \
    --entrypoint python \
    backend-test /app/scripts/nfr/load_test.py \
        --base-url http://web \
        --users "$PERF_USERS" \
        --professors "$PERF_PROFESSORS" \
        --duration "$PERF_DURATION" \
        --ramp-up "$PERF_RAMP_UP" \
        --report /app/reports/nfr/load.json \
        --markdown /app/reports/nfr/load.md \
        $enforce_flag

echo "==> Running navigation and upload timings"
(
    cd frontend
    E2E_BASE_URL=http://localhost:18081 \
        E2E_DEMO_PASSWORD="$password" \
        E2E_PERF=1 \
        E2E_PERF_ENFORCE="$PERF_ENFORCE" \
        npx playwright test --project=chromium e2e/perf.spec.ts
)

stop_sampler

echo "==> Building the memory report"
python3 scripts/nfr/memory_report.py \
    --samples reports/nfr/memory-samples.jsonl \
    --output reports/nfr/memory.json

python3 - <<'PY'
import json
from pathlib import Path

load_path = Path("reports/nfr/load.json")
memory_path = Path("reports/nfr/memory.json")
if load_path.exists() and memory_path.exists():
    load = json.loads(load_path.read_text(encoding="utf-8"))
    memory = json.loads(memory_path.read_text(encoding="utf-8"))
    load["memory"] = memory
    load_path.write_text(
        json.dumps(load, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path = Path("reports/nfr/load.md")
    if markdown_path.exists():
        with markdown_path.open("a", encoding="utf-8") as handle:
            handle.write("\n## Memoria de contenedores\n\n")
            handle.write(f"- Pico total: {memory['peak_total_mib']} MiB\n")
            handle.write(f"- Media: {memory['mean_total_mib']} MiB\n")
            handle.write(
                f"- Instancia sugerida: {memory['recommended_instance_mib']} MiB\n"
            )
PY

echo "Performance OK: reports/nfr/load.json, navigation.json, memory.json"

if [ "$PERF_CLEANUP" = "1" ]; then
    echo "==> Removing the performance stack"
    compose_perf down -v
fi
