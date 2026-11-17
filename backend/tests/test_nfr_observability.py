import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from starlette.requests import Request
from starlette.types import Scope

from app.core.audit.models import RegistroAuditoria
from app.core.audit.service import purge_audit_logs
from app.core.config import settings
from app.core.http import get_client_ip
from app.core.logging import JsonFormatter
from app.db.session import SessionLocal
from tests.nfr_helpers import PASSWORD, create_user, login, setup_rbac_scenario

pytestmark = pytest.mark.nfr


async def _fetch_audit_rows() -> list[RegistroAuditoria]:
    async with SessionLocal() as db:
        result = await db.scalars(
            select(RegistroAuditoria).order_by(RegistroAuditoria.fecha)
        )
        return list(result.all())


def _make_request(
    headers: dict[str, str],
    client: tuple[str, int] | None,
) -> Request:
    scope = cast(
        Scope,
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "raw_path": b"/",
            "root_path": "",
            "scheme": "http",
            "query_string": b"",
            "headers": [
                (key.lower().encode(), value.encode()) for key, value in headers.items()
            ],
            "client": client,
            "server": ("testserver", 80),
        },
    )
    return Request(scope)


def _deliverable_payload() -> dict[str, Any]:
    return {
        "title": "Entregable auditado",
        "description": "Descripción del entregable auditado",
        "deadline_at": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        "allowed_formats": ["pdf"],
        "max_file_size_mb": 50,
    }


async def test_audit_rows_cover_critical_actions(client: AsyncClient) -> None:
    scenario = await setup_rbac_scenario(client)

    initial_rows = await _fetch_audit_rows()
    initial_actions = {row.accion for row in initial_rows}
    assert {
        "sesion.iniciar",
        "proyecto.crear",
        "hito.crear",
        "entregable.crear",
        "entrega.crear",
    } <= initial_actions

    project_row = next(row for row in initial_rows if row.accion == "proyecto.crear")
    assert project_row.entidad == "proyecto"
    assert project_row.entidad_id == str(scenario.project["id"])

    submission_row = next(row for row in initial_rows if row.accion == "entrega.crear")
    assert submission_row.entidad == "entrega"
    assert submission_row.entidad_id == str(scenario.submission["id"])

    await login(client, scenario.manager.correo)
    project_id = str(scenario.project["id"])
    pending_id = str(scenario.pending_deliverable["id"])
    submitted_id = str(scenario.submitted_deliverable["id"])

    project_update = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "topic": "Proyecto auditado",
            "project_type": "memoir",
            "manager_emails": [scenario.manager.correo],
            "collaborator_emails": [scenario.collaborator.correo],
        },
    )
    assert project_update.status_code == 200, project_update.text

    milestone = await client.post(
        f"/api/v1/projects/{project_id}/milestones",
        json={"name": "Hito auditado", "position": 2},
    )
    assert milestone.status_code == 201, milestone.text

    deliverable = await client.post(
        f"/api/v1/milestones/{milestone.json()['id']}/deliverables",
        json=_deliverable_payload(),
    )
    assert deliverable.status_code == 201, deliverable.text

    edited = await client.patch(
        f"/api/v1/deliverables/{pending_id}",
        json=_deliverable_payload(),
    )
    assert edited.status_code == 200, edited.text

    review = await client.post(
        f"/api/v1/deliverables/{submitted_id}/reviews",
        data={"decision": "approved"},
    )
    assert review.status_code == 201, review.text

    message = await client.post(
        f"/api/v1/deliverables/{pending_id}/messages",
        json={"body": "Mensaje auditado"},
    )
    assert message.status_code == 201, message.text

    download = await client.get(f"/api/v1/files/{scenario.file_id}/download")
    assert download.status_code == 200

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    rows = await _fetch_audit_rows()
    actions = {row.accion for row in rows}
    expected_entities = {
        "sesion.iniciar": "sesion",
        "sesion.cerrar": "sesion",
        "proyecto.crear": "proyecto",
        "proyecto.editar": "proyecto",
        "hito.crear": "hito",
        "entregable.crear": "entregable",
        "entregable.editar": "entregable",
        "entrega.crear": "entrega",
        "revision.crear": "revision",
        "comentario.crear": "comentario",
        "archivo.descargar": "archivo",
    }
    assert set(expected_entities) <= actions

    for action, entity in expected_entities.items():
        matching = [row for row in rows if row.accion == action]
        assert matching, action
        assert all(row.entidad == entity for row in matching)
        assert all(row.entidad_id for row in matching)
        assert all(row.ip for row in matching)

    for row in rows:
        stored_text = row.accion + row.entidad + row.entidad_id + (row.ip or "")
        assert PASSWORD not in stored_text

    assert all(row.usuario_id is not None for row in rows)


async def test_purge_audit_logs() -> None:
    user = await create_user("audit@example.com")
    now = datetime.now(UTC)

    async with SessionLocal() as db:
        old_ip = RegistroAuditoria(
            usuario_id=user.id,
            accion="ip.antigua",
            entidad="usuario",
            entidad_id=str(user.id),
            fecha=now - timedelta(days=100),
            ip="203.0.113.10",
        )
        old_row = RegistroAuditoria(
            usuario_id=user.id,
            accion="fila.antigua",
            entidad="usuario",
            entidad_id=str(user.id),
            fecha=now - timedelta(days=400),
            ip="203.0.113.11",
        )
        recent = RegistroAuditoria(
            usuario_id=user.id,
            accion="reciente",
            entidad="usuario",
            entidad_id=str(user.id),
            fecha=now - timedelta(days=1),
            ip="203.0.113.12",
        )
        db.add_all([old_ip, old_row, recent])
        await db.commit()

        anonymized, deleted = await purge_audit_logs(db, now=now)
        assert (anonymized, deleted) == (1, 1)

        remaining = (await db.scalars(select(RegistroAuditoria))).all()

    by_action = {row.accion: row for row in remaining}
    assert "fila.antigua" not in by_action
    assert by_action["ip.antigua"].ip is None
    assert by_action["reciente"].ip == "203.0.113.12"


def test_json_formatter() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Acción %s",
        args=("segura",),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "Acción segura"
    assert "timestamp" in payload


def test_json_formatter_includes_exception() -> None:
    formatter = JsonFormatter()
    try:
        raise ValueError("fallo controlado")
    except ValueError:
        record = logging.LogRecord(
            name="app.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Error de prueba",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))

    assert "ValueError: fallo controlado" in payload["exception"]


def test_uvicorn_log_config_uses_json_formatter() -> None:
    config_path = Path(__file__).resolve().parents[1] / "logging.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["formatters"]["json"]["()"] == "app.core.logging.JsonFormatter"
    assert config["handlers"]["default"]["formatter"] == "json"


async def test_login_does_not_log_credentials(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    user = await create_user("logs@example.com")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.correo, "password": PASSWORD},
    )

    assert response.status_code == 200
    token = client.cookies.get("hito_session")
    assert token is not None
    assert PASSWORD not in caplog.text
    assert token not in caplog.text


def test_get_client_ip_respects_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _make_request(
        {"x-real-ip": "203.0.113.20"},
        client=("10.0.0.5", 12345),
    )

    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    assert get_client_ip(request) == "203.0.113.20"

    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    assert get_client_ip(request) == "10.0.0.5"


def test_get_client_ip_uses_first_forwarded_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _make_request(
        {"x-forwarded-for": "203.0.113.30, 10.0.0.5"},
        client=("10.0.0.5", 12345),
    )
    monkeypatch.setattr(settings, "trust_proxy_headers", True)

    assert get_client_ip(request) == "203.0.113.30"


def test_get_client_ip_handles_missing_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _make_request({}, client=None)
    monkeypatch.setattr(settings, "trust_proxy_headers", False)

    assert get_client_ip(request) == "unknown"
