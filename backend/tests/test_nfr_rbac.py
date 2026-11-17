from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.main import app
from tests.nfr_helpers import (
    PDF_BYTES,
    RbacScenario,
    login,
    post_submission,
    setup_rbac_scenario,
    submit,
)

pytestmark = pytest.mark.nfr

ROUTE_ACCESS: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/auth/login"): "public",
    ("POST", "/api/v1/auth/logout"): "public",
    ("GET", "/api/v1/auth/me"): "authenticated",
    ("GET", "/api/v1/projects"): "authenticated",
    ("POST", "/api/v1/projects"): "professor",
    ("GET", "/api/v1/projects/{project_id}"): "participant",
    ("PATCH", "/api/v1/projects/{project_id}"): "manager",
    ("POST", "/api/v1/projects/{project_id}/milestones"): "manager",
    ("POST", "/api/v1/milestones/{milestone_id}/deliverables"): "manager",
    ("PATCH", "/api/v1/deliverables/{deliverable_id}"): "manager",
    ("GET", "/api/v1/deliverables/{deliverable_id}"): "participant",
    ("GET", "/api/v1/deliverables/{deliverable_id}/submissions"): "manager",
    ("POST", "/api/v1/deliverables/{deliverable_id}/submissions"): "collaborator",
    ("POST", "/api/v1/deliverables/{deliverable_id}/reviews"): "manager",
    ("POST", "/api/v1/deliverables/{deliverable_id}/messages"): "participant",
    ("GET", "/api/v1/reviews/pending"): "authenticated",
    ("GET", "/api/v1/files/{file_id}/download"): "participant",
    ("GET", "/api/v1/meta"): "public",
    ("GET", "/health/live"): "public",
    ("GET", "/health/ready"): "public",
}


def _project_payload(manager_email: str, collaborator_email: str) -> dict[str, Any]:
    return {
        "topic": "Proyecto actualizado",
        "project_type": "memoir",
        "manager_emails": [manager_email],
        "collaborator_emails": [collaborator_email],
    }


def _milestone_payload() -> dict[str, Any]:
    return {"name": "Hito nuevo", "position": 2}


def _deliverable_payload() -> dict[str, Any]:
    return {
        "title": "Entregable nuevo",
        "description": "Descripción del entregable nuevo",
        "deadline_at": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        "allowed_formats": ["pdf"],
        "max_file_size_mb": 50,
    }


def _submission_files() -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", ("nfr.pdf", PDF_BYTES, "application/pdf"))]


def test_openapi_routes_are_classified() -> None:
    documented = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in {"get", "post", "patch", "put", "delete"}
    }

    assert documented == set(ROUTE_ACCESS)


PROTECTED_REQUESTS: list[tuple[str, str, dict[str, Any]]] = [
    ("GET", "/api/v1/auth/me", {}),
    ("GET", "/api/v1/projects", {}),
    (
        "POST",
        "/api/v1/projects",
        {
            "json": {
                "topic": "Proyecto anónimo",
                "project_type": "memoir",
                "manager_emails": [],
                "collaborator_emails": ["student@example.com"],
            }
        },
    ),
    ("GET", "/api/v1/projects/{project_id}", {}),
    (
        "PATCH",
        "/api/v1/projects/{project_id}",
        {
            "json": {
                "topic": "Proyecto anónimo",
                "project_type": "memoir",
                "manager_emails": ["manager@example.com"],
                "collaborator_emails": ["student@example.com"],
            }
        },
    ),
    (
        "POST",
        "/api/v1/projects/{project_id}/milestones",
        {"json": _milestone_payload()},
    ),
    (
        "POST",
        "/api/v1/milestones/{milestone_id}/deliverables",
        {"json": _deliverable_payload()},
    ),
    (
        "PATCH",
        "/api/v1/deliverables/{deliverable_id}",
        {"json": _deliverable_payload()},
    ),
    ("GET", "/api/v1/deliverables/{deliverable_id}", {}),
    ("GET", "/api/v1/deliverables/{deliverable_id}/submissions", {}),
    (
        "POST",
        "/api/v1/deliverables/{deliverable_id}/submissions",
        {"files": _submission_files()},
    ),
    (
        "POST",
        "/api/v1/deliverables/{deliverable_id}/reviews",
        {"data": {"decision": "approved"}},
    ),
    (
        "POST",
        "/api/v1/deliverables/{deliverable_id}/messages",
        {"json": {"body": "Mensaje anónimo"}},
    ),
    ("GET", "/api/v1/reviews/pending", {}),
    ("GET", "/api/v1/files/{file_id}/download", {}),
]


@pytest.mark.parametrize(("method", "path_template", "kwargs"), PROTECTED_REQUESTS)
async def test_anonymous_requests_are_rejected(
    client: AsyncClient,
    method: str,
    path_template: str,
    kwargs: dict[str, Any],
) -> None:
    path = path_template.format(
        project_id=uuid4(),
        milestone_id=uuid4(),
        deliverable_id=uuid4(),
        file_id=uuid4(),
    )

    response = await client.request(method, path, **kwargs)

    assert response.status_code == 401, (method, path, response.text)


async def _project_resource_requests(
    scenario: RbacScenario,
) -> list[tuple[str, str, dict[str, Any]]]:
    project_id = str(scenario.project["id"])
    milestone_id = str(scenario.milestone["id"])
    pending_id = str(scenario.pending_deliverable["id"])
    submitted_id = str(scenario.submitted_deliverable["id"])
    return [
        ("GET", f"/api/v1/projects/{project_id}", {}),
        (
            "PATCH",
            f"/api/v1/projects/{project_id}",
            {
                "json": _project_payload(
                    scenario.manager.correo,
                    scenario.collaborator.correo,
                )
            },
        ),
        (
            "POST",
            f"/api/v1/projects/{project_id}/milestones",
            {"json": _milestone_payload()},
        ),
        (
            "POST",
            f"/api/v1/milestones/{milestone_id}/deliverables",
            {"json": _deliverable_payload()},
        ),
        ("GET", f"/api/v1/deliverables/{pending_id}", {}),
        (
            "PATCH",
            f"/api/v1/deliverables/{pending_id}",
            {"json": _deliverable_payload()},
        ),
        ("GET", f"/api/v1/deliverables/{submitted_id}/submissions", {}),
        (
            "POST",
            f"/api/v1/deliverables/{pending_id}/submissions",
            {"files": _submission_files()},
        ),
        (
            "POST",
            f"/api/v1/deliverables/{submitted_id}/reviews",
            {"data": {"decision": "approved"}},
        ),
        (
            "POST",
            f"/api/v1/deliverables/{pending_id}/messages",
            {"json": {"body": "Mensaje ajeno"}},
        ),
        ("GET", f"/api/v1/files/{scenario.file_id}/download", {}),
    ]


async def test_non_participant_gets_not_found_for_project_resources(
    client: AsyncClient,
) -> None:
    scenario = await setup_rbac_scenario(client)
    await login(client, scenario.outsider.correo)

    for method, path, kwargs in await _project_resource_requests(scenario):
        response = await client.request(method, path, **kwargs)
        assert response.status_code == 404, (method, path, response.text)


async def test_collaborator_gets_forbidden_for_manager_actions(
    client: AsyncClient,
) -> None:
    scenario = await setup_rbac_scenario(client)
    await login(client, scenario.collaborator.correo)
    project_id = str(scenario.project["id"])
    milestone_id = str(scenario.milestone["id"])
    pending_id = str(scenario.pending_deliverable["id"])
    submitted_id = str(scenario.submitted_deliverable["id"])

    requests: list[tuple[str, str, dict[str, Any]]] = [
        (
            "PATCH",
            f"/api/v1/projects/{project_id}",
            {
                "json": _project_payload(
                    scenario.manager.correo,
                    scenario.collaborator.correo,
                )
            },
        ),
        (
            "POST",
            f"/api/v1/projects/{project_id}/milestones",
            {"json": _milestone_payload()},
        ),
        (
            "POST",
            f"/api/v1/milestones/{milestone_id}/deliverables",
            {"json": _deliverable_payload()},
        ),
        (
            "PATCH",
            f"/api/v1/deliverables/{pending_id}",
            {"json": _deliverable_payload()},
        ),
        ("GET", f"/api/v1/deliverables/{submitted_id}/submissions", {}),
        (
            "POST",
            f"/api/v1/deliverables/{submitted_id}/reviews",
            {"data": {"decision": "approved"}},
        ),
    ]

    for method, path, kwargs in requests:
        response = await client.request(method, path, **kwargs)
        assert response.status_code == 403, (method, path, response.text)


async def test_manager_cannot_submit(client: AsyncClient) -> None:
    scenario = await setup_rbac_scenario(client)
    await login(client, scenario.manager.correo)

    response = await post_submission(
        client,
        str(scenario.pending_deliverable["id"]),
        files=_submission_files(),
    )

    assert response.status_code == 403


async def test_student_cannot_create_project(client: AsyncClient) -> None:
    scenario = await setup_rbac_scenario(client)
    await login(client, scenario.collaborator.correo)

    response = await client.post(
        "/api/v1/projects",
        json={
            "topic": "Proyecto de estudiante",
            "project_type": "memoir",
            "manager_emails": [],
            "collaborator_emails": [scenario.collaborator.correo],
        },
    )

    assert response.status_code == 403


async def test_participants_can_read_their_project_resources(
    client: AsyncClient,
) -> None:
    scenario = await setup_rbac_scenario(client)
    project_id = str(scenario.project["id"])
    pending_id = str(scenario.pending_deliverable["id"])
    submitted_id = str(scenario.submitted_deliverable["id"])

    for user, expected_role in (
        (scenario.manager, "manager"),
        (scenario.collaborator, "collaborator"),
    ):
        await login(client, user.correo)

        project = await client.get(f"/api/v1/projects/{project_id}")
        assert project.status_code == 200
        assert project.json()["my_role"] == expected_role

        pending = await client.get(f"/api/v1/deliverables/{pending_id}")
        assert pending.status_code == 200
        assert pending.json()["my_role"] == expected_role

        submitted = await client.get(f"/api/v1/deliverables/{submitted_id}")
        assert submitted.status_code == 200
        assert submitted.json()["my_role"] == expected_role

        listing = await client.get("/api/v1/projects")
        assert listing.status_code == 200
        assert [item["id"] for item in listing.json()] == [project_id]

    await login(client, scenario.outsider.correo)
    assert (await client.get(f"/api/v1/projects/{project_id}")).status_code == 404
    assert (await client.get(f"/api/v1/deliverables/{pending_id}")).status_code == 404
    assert (await client.get("/api/v1/projects")).json() == []


async def test_pending_reviews_are_scoped_by_role(client: AsyncClient) -> None:
    scenario = await setup_rbac_scenario(client)
    submitted_id = str(scenario.submitted_deliverable["id"])

    await login(client, scenario.manager.correo)
    manager_pending = await client.get("/api/v1/reviews/pending")
    assert manager_pending.status_code == 200
    assert [item["deliverable_id"] for item in manager_pending.json()] == [submitted_id]

    await login(client, scenario.collaborator.correo)
    collaborator_pending = await client.get("/api/v1/reviews/pending")
    assert collaborator_pending.status_code == 200
    assert collaborator_pending.json() == []

    await login(client, scenario.outsider.correo)
    outsider_pending = await client.get("/api/v1/reviews/pending")
    assert outsider_pending.status_code == 200
    assert outsider_pending.json() == []


async def test_download_and_history_are_scoped_by_role(client: AsyncClient) -> None:
    scenario = await setup_rbac_scenario(client)
    deliverable_id = str(scenario.submitted_deliverable["id"])

    await login(client, scenario.collaborator.correo)
    second = await submit(
        client,
        deliverable_id,
        files=[("files", ("v2.pdf", b"version-2", "application/pdf"))],
    )
    second_file_id = str(second["files"][0]["id"])

    await login(client, scenario.manager.correo)
    assert (
        await client.get(f"/api/v1/files/{scenario.file_id}/download")
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/files/{second_file_id}/download")
    ).status_code == 200
    history = await client.get(f"/api/v1/deliverables/{deliverable_id}/submissions")
    assert history.status_code == 200
    assert [item["version"] for item in history.json()] == [1, 2]

    await login(client, scenario.collaborator.correo)
    assert (
        await client.get(f"/api/v1/files/{scenario.file_id}/download")
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/files/{second_file_id}/download")
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/deliverables/{deliverable_id}/submissions")
    ).status_code == 403

    await login(client, scenario.outsider.correo)
    assert (
        await client.get(f"/api/v1/files/{second_file_id}/download")
    ).status_code == 404


async def test_manager_can_use_manager_actions(client: AsyncClient) -> None:
    scenario = await setup_rbac_scenario(client)
    await login(client, scenario.manager.correo)
    project_id = str(scenario.project["id"])
    pending_id = str(scenario.pending_deliverable["id"])
    submitted_id = str(scenario.submitted_deliverable["id"])

    project = await client.patch(
        f"/api/v1/projects/{project_id}",
        json=_project_payload(scenario.manager.correo, scenario.collaborator.correo),
    )
    assert project.status_code == 200, project.text

    milestone = await client.post(
        f"/api/v1/projects/{project_id}/milestones",
        json=_milestone_payload(),
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
