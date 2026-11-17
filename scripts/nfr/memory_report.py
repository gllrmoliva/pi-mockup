#!/usr/bin/env python3
import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


def _read_samples(path: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    if not path.exists():
        return samples
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            samples.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return samples


def _report(samples: list[dict[str, Any]]) -> dict[str, Any]:
    totals = [float(sample["total_mib"]) for sample in samples]
    by_container: dict[str, list[float]] = {}
    for sample in samples:
        for container in sample.get("containers", []):
            by_container.setdefault(str(container["name"]), []).append(
                float(container["memory_mib"])
            )

    peak_total = max(totals, default=0.0)
    peak_by_container = {
        name: round(max(values), 2) for name, values in sorted(by_container.items())
    }
    recommended = math.ceil(peak_total * 1.3 / 128) * 128 if peak_total else 0

    return {
        "samples": len(samples),
        "peak_total_mib": round(peak_total, 2),
        "mean_total_mib": round(statistics.fmean(totals), 2) if totals else 0.0,
        "peak_by_container": peak_by_container,
        "recommended_instance_mib": recommended,
        "recommendation": (
            "Pico de contenedores + 30 % para SO, Nginx y picos. "
            "Confirmar el precio vigente de AWS Lightsail/EC2."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume muestras de memoria Docker.")
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = _report(_read_samples(args.samples))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Memoria: pico={report['peak_total_mib']} MiB, "
        f"media={report['mean_total_mib']} MiB, "
        f"instancia sugerida={report['recommended_instance_mib']} MiB"
    )


if __name__ == "__main__":
    main()
