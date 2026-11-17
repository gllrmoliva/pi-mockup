#!/usr/bin/env python3
import json
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime

RUNNING = True


def _stop(_signum: int, _frame: object) -> None:
    global RUNNING
    RUNNING = False


def _to_mib(value: str) -> float:
    token = value.strip().split()[0]
    units = ("GiB", "MiB", "KiB", "B")
    for unit in units:
        if token.endswith(unit):
            number = float(token[: -len(unit)])
            factors = {"GiB": 1024.0, "MiB": 1.0, "KiB": 1 / 1024, "B": 1 / 1024**2}
            return round(number * factors[unit], 2)
    return 0.0


def _sample() -> dict[str, object] | None:
    try:
        output = subprocess.check_output(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            text=True,
            timeout=30,
        )
    except Exception as exc:
        print(f"docker stats failed: {exc}", file=sys.stderr)
        return None

    containers: list[dict[str, object]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        name = str(data.get("Name", ""))
        if not name.startswith("hito_perf-") or "backend-test" in name:
            continue
        usage = str(data.get("MemUsage", "0MiB / 0MiB")).split("/")[0]
        memory_mib = _to_mib(usage)
        containers.append(
            {
                "name": name,
                "memory_mib": memory_mib,
                "memory_percent": str(data.get("MemPerc", "")),
            }
        )

    if not containers:
        return None

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "containers": containers,
        "total_mib": round(
            sum(float(container["memory_mib"]) for container in containers), 2
        ),
    }


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while RUNNING:
        sample = _sample()
        if sample is not None:
            print(json.dumps(sample, ensure_ascii=False), flush=True)
        time.sleep(5)


if __name__ == "__main__":
    main()
