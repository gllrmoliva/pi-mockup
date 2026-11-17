#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import random
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

READ_PROJECTS_PERCENT = 35
READ_PROJECT_PERCENT = 20
READ_DELIVERABLE_PERCENT = 15
READ_PENDING_PERCENT = 10
DOWNLOAD_PERCENT = 15
WRITE_PERCENT = 5


@dataclass
class VirtualUser:
    index: int
    email: str
    is_professor: bool
    client: httpx.AsyncClient
    rng: random.Random
    project_ids: list[str] = field(default_factory=list)
    deliverable_ids: list[str] = field(default_factory=list)
    open_deliverable_ids: list[str] = field(default_factory=list)
    submitted_deliverable_ids: list[str] = field(default_factory=list)
    file_ids: dict[str, str] = field(default_factory=dict)


@dataclass
class RequestSample:
    action: str
    status: int
    latency_ms: float
    expected: bool


def _password() -> str:
    value = os.environ.get("PERF_PASSWORD")
    if not value:
        raise SystemExit("PERF_PASSWORD is required.")
    return value


def _percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percent / 100) * (len(ordered) - 1))))
    return round(ordered[index], 2)


def _summary(samples: list[RequestSample]) -> dict[str, Any]:
    latencies = [sample.latency_ms for sample in samples]
    errors = [sample for sample in samples if not sample.expected]
    return {
        "requests": len(samples),
        "errors": len(errors),
        "error_rate": round(len(errors) / len(samples), 4) if samples else 0.0,
        "latency_ms": {
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
            "p99": _percentile(latencies, 99),
            "mean": round(statistics.fmean(latencies), 2) if latencies else 0.0,
        },
    }


async def _get_json(
    vu: VirtualUser,
    path: str,
) -> dict[str, Any]:
    response = await vu.client.get(path)
    response.raise_for_status()
    return response.json()


async def _setup_user(
    index: int,
    base_url: str,
    password: str,
    professors: int,
) -> VirtualUser:
    is_professor = index < professors
    email = (
        f"profe{index + 1:04d}@perf.example.com"
        if is_professor
        else f"est{index - professors + 1:04d}@perf.example.com"
    )
    client = httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        follow_redirects=False,
    )
    vu = VirtualUser(
        index=index,
        email=email,
        is_professor=is_professor,
        client=client,
        rng=random.Random(1000 + index),
    )

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    login.raise_for_status()

    projects = await _get_json(vu, "/api/v1/projects")
    vu.project_ids = [str(project["id"]) for project in projects]
    if not vu.project_ids:
        raise RuntimeError(f"{email} no tiene proyectos.")

    for project_id in vu.project_ids[:2]:
        detail = await _get_json(vu, f"/api/v1/projects/{project_id}")
        for milestone in detail["milestones"]:
            for deliverable in milestone["deliverables"]:
                deliverable_id = str(deliverable["id"])
                vu.deliverable_ids.append(deliverable_id)
                if deliverable["status"] != "approved":
                    vu.open_deliverable_ids.append(deliverable_id)
                if deliverable["status"] == "submitted":
                    vu.submitted_deliverable_ids.append(deliverable_id)

    return vu


async def _record(
    vu: VirtualUser,
    samples: list[RequestSample],
    action: str,
    method: str,
    url: str,
    *,
    expected_statuses: set[int],
    **kwargs: Any,
) -> None:
    started = time.perf_counter()
    status = 0
    try:
        response = await vu.client.request(method, url, **kwargs)
        status = response.status_code
        if action == "download":
            _ = response.content
    except Exception:
        status = 0
    finally:
        latency_ms = (time.perf_counter() - started) * 1000
        samples.append(
            RequestSample(
                action=action,
                status=status,
                latency_ms=round(latency_ms, 2),
                expected=status in expected_statuses and status != 0,
            )
        )


async def _file_id(vu: VirtualUser) -> str | None:
    if not vu.deliverable_ids:
        return None
    deliverable_id = vu.rng.choice(vu.deliverable_ids)
    cached = vu.file_ids.get(deliverable_id)
    if cached is not None:
        return cached
    try:
        detail = await _get_json(vu, f"/api/v1/deliverables/{deliverable_id}")
    except Exception:
        return None
    latest = detail.get("latest_submission")
    if not latest:
        return None
    files = latest.get("files") or []
    if not files:
        return None
    file_id = str(files[0]["id"])
    vu.file_ids[deliverable_id] = file_id
    return file_id


async def _action(
    vu: VirtualUser,
    samples: list[RequestSample],
) -> None:
    draw = vu.rng.uniform(0, 100)

    if draw < READ_PROJECTS_PERCENT:
        await _record(
            vu,
            samples,
            "projects",
            "GET",
            "/api/v1/projects",
            expected_statuses={200},
        )
        return

    if draw < READ_PROJECTS_PERCENT + READ_PROJECT_PERCENT:
        if not vu.project_ids:
            return
        project_id = vu.rng.choice(vu.project_ids)
        await _record(
            vu,
            samples,
            "project_detail",
            "GET",
            f"/api/v1/projects/{project_id}",
            expected_statuses={200},
        )
        return

    if (
        draw
        < READ_PROJECTS_PERCENT
        + READ_PROJECT_PERCENT
        + READ_DELIVERABLE_PERCENT
    ):
        if not vu.deliverable_ids:
            return
        deliverable_id = vu.rng.choice(vu.deliverable_ids)
        await _record(
            vu,
            samples,
            "deliverable_detail",
            "GET",
            f"/api/v1/deliverables/{deliverable_id}",
            expected_statuses={200},
        )
        return

    if (
        draw
        < READ_PROJECTS_PERCENT
        + READ_PROJECT_PERCENT
        + READ_DELIVERABLE_PERCENT
        + READ_PENDING_PERCENT
    ):
        await _record(
            vu,
            samples,
            "pending_reviews",
            "GET",
            "/api/v1/reviews/pending",
            expected_statuses={200},
        )
        return

    if (
        draw
        < READ_PROJECTS_PERCENT
        + READ_PROJECT_PERCENT
        + READ_DELIVERABLE_PERCENT
        + READ_PENDING_PERCENT
        + DOWNLOAD_PERCENT
    ):
        file_id = await _file_id(vu)
        if file_id is None:
            if vu.project_ids:
                await _record(
                    vu,
                    samples,
                    "project_detail",
                    "GET",
                    f"/api/v1/projects/{vu.rng.choice(vu.project_ids)}",
                    expected_statuses={200},
                )
            return
        await _record(
            vu,
            samples,
            "download",
            "GET",
            f"/api/v1/files/{file_id}/download",
            expected_statuses={200},
        )
        return

    # 5 % writes: message, submission (student) or review (professor).
    write_draw = vu.rng.uniform(0, 100)
    if write_draw < 60:
        if not vu.deliverable_ids:
            return
        await _record(
            vu,
            samples,
            "message",
            "POST",
            f"/api/v1/deliverables/{vu.rng.choice(vu.deliverable_ids)}/messages",
            expected_statuses={201},
            json={"body": f"Mensaje de carga {vu.index}"},
        )
        return

    if write_draw < 80 and not vu.is_professor:
        if not vu.open_deliverable_ids:
            return
        deliverable_id = vu.rng.choice(vu.open_deliverable_ids)
        await _record(
            vu,
            samples,
            "submission",
            "POST",
            f"/api/v1/deliverables/{deliverable_id}/submissions",
            expected_statuses={201, 409},
            data={"link_url": f"https://example.com/load/{vu.index}/{time.time_ns()}"},
        )
        return

    if vu.is_professor and vu.submitted_deliverable_ids:
        deliverable_id = vu.rng.choice(vu.submitted_deliverable_ids)
        await _record(
            vu,
            samples,
            "review",
            "POST",
            f"/api/v1/deliverables/{deliverable_id}/reviews",
            expected_statuses={201, 409},
            data={"decision": "approved"},
        )
        return

    await _record(
        vu,
        samples,
        "message",
        "POST",
        f"/api/v1/deliverables/{vu.rng.choice(vu.deliverable_ids)}/messages",
        expected_statuses={201},
        json={"body": f"Mensaje de carga {vu.index}"},
    )


async def _run_user(
    vu: VirtualUser,
    samples: list[RequestSample],
    stop_at: float,
) -> None:
    try:
        while time.monotonic() < stop_at:
            await _action(vu, samples)
            await asyncio.sleep(vu.rng.uniform(0.5, 1.5))
    finally:
        await vu.client.aclose()


async def run_load_test(args: argparse.Namespace) -> dict[str, Any]:
    samples: list[RequestSample] = []
    users: list[VirtualUser] = []
    setup_errors = 0
    start = time.monotonic()
    stop_at = start + args.ramp_up + args.duration

    async def setup(index: int) -> VirtualUser | None:
        nonlocal setup_errors
        await asyncio.sleep(index * args.ramp_up / args.users)
        try:
            return await _setup_user(
                index,
                args.base_url,
                args.password,
                args.professors,
            )
        except Exception as exc:
            setup_errors += 1
            print(f"Setup failed for user {index}: {exc}", file=sys.stderr)
            return None

    users = [
        user
        for user in await asyncio.gather(
            *(setup(index) for index in range(args.users))
        )
        if user is not None
    ]

    if not users:
        raise SystemExit("Ningún usuario virtual pudo iniciar sesión.")

    tasks = [
        asyncio.create_task(_run_user(vu, samples, stop_at)) for vu in users
    ]
    await asyncio.gather(*tasks)

    elapsed = time.monotonic() - start
    totals = _summary(samples)
    by_action: dict[str, Any] = defaultdict(lambda: {"samples": []})
    for sample in samples:
        by_action[sample.action]["samples"].append(sample)

    actions = {
        action: _summary(data["samples"]) for action, data in by_action.items()
    }
    p95 = totals["latency_ms"]["p95"]
    error_rate = totals["error_rate"]
    passed = p95 <= args.p95_ms and error_rate < args.max_error_rate

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "users": args.users,
        "professors": args.professors,
        "students": args.users - args.professors,
        "duration_seconds": round(elapsed, 2),
        "target_duration_seconds": args.duration,
        "ramp_up_seconds": args.ramp_up,
        "setup_errors": setup_errors,
        "mix": {
            "read_projects_percent": READ_PROJECTS_PERCENT,
            "read_project_percent": READ_PROJECT_PERCENT,
            "read_deliverable_percent": READ_DELIVERABLE_PERCENT,
            "read_pending_percent": READ_PENDING_PERCENT,
            "download_percent": DOWNLOAD_PERCENT,
            "write_percent": WRITE_PERCENT,
        },
        "targets": {
            "p95_ms": args.p95_ms,
            "max_error_rate": args.max_error_rate,
        },
        "totals": totals,
        "by_action": actions,
        "throughput_rps": round(len(samples) / elapsed, 2) if elapsed else 0.0,
        "passed": passed,
    }
    return report


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Reporte de carga",
        "",
        f"- Fecha: {report['generated_at']}",
        f"- URL: {report['base_url']}",
        f"- Usuarios: {report['users']} ({report['professors']} profesores, "
        f"{report['students']} estudiantes)",
        f"- Duración: {report['duration_seconds']} s",
        f"- Throughput: {report['throughput_rps']} req/s",
        f"- Requests: {report['totals']['requests']}",
        f"- Error rate: {report['totals']['error_rate']}",
        f"- p95: {report['totals']['latency_ms']['p95']} ms",
        f"- Resultado: {'PASS' if report['passed'] else 'FAIL'}",
        "",
        "| Acción | Requests | Errores | p50 | p95 | p99 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for action, data in sorted(report["by_action"].items()):
        lines.append(
            f"| {action} | {data['requests']} | {data['errors']} | "
            f"{data['latency_ms']['p50']} | {data['latency_ms']['p95']} | "
            f"{data['latency_ms']['p99']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prueba de carga de Hito.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--professors", type=int, default=30)
    parser.add_argument("--duration", type=int, default=900)
    parser.add_argument("--ramp-up", type=int, default=30)
    parser.add_argument("--p95-ms", type=float, default=500.0)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--password", default=None)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--enforce", action="store_true")
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args()
    args.password = args.password or _password()
    report = asyncio.run(run_load_test(args))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = args.markdown or args.report.with_suffix(".md")
    _write_markdown(report, markdown)
    print(
        f"Load test: {report['totals']['requests']} requests, "
        f"p95={report['totals']['latency_ms']['p95']} ms, "
        f"error_rate={report['totals']['error_rate']}, "
        f"passed={report['passed']}"
    )
    if args.enforce and not report["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
