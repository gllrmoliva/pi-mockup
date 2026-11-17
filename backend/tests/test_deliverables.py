from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Usuario
from app.modules.auth.security import hash_password
from app.modules.deliverables.models import Entrega, Entregable

PASSWORD = "TestPassword123!"
PDF_BYTES = b"%PDF-1.4\ncontenido de prueba\n"


async def create_user(
    email: str,
    *,
    user_type: UserType = UserType.PROFESSOR,
) -> Usuario:
    async with SessionLocal() as db:
        user = Usuario(
            nombre=email.split("@")[0].replace(".", " ").title(),
            correo=email.lower(),
            tipo=user_type,
            credencial=hash_password(PASSWORD),
            estado=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text


async def create_project(
    client: AsyncClient, collaborator_email: str
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/projects",
        json={
            "topic": "Proyecto de entregables",
            "project_type": "memoir",
            "manager_emails": [],
            "collaborator_emails": [collaborator_email],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_milestone(
    client: AsyncClient,
    project_id: str,
    *,
    name: str = "Hito de prueba",
    position: int = 1,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/projects/{project_id}/milestones",
        json={"name": name, "position": position},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_deliverable(
    client: AsyncClient,
    milestone_id: str,
    *,
    title: str = "Entregable de prueba",
    deadline: datetime | None = None,
    formats: list[str] | None = None,
    max_file_size_mb: int = 50,
) -> dict[str, Any]:
    due = deadline or (datetime.now(UTC) + timedelta(days=10))
    response = await client.post(
        f"/api/v1/milestones/{milestone_id}/deliverables",
        json={
            "title": title,
            "description": "Descripción del entregable",
            "deadline_at": due.isoformat(),
            "allowed_formats": formats or ["pdf", "zip"],
            "max_file_size_mb": max_file_size_mb,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def upload(
    client: AsyncClient,
    deliverable_id: str,
    files: list[tuple[str, tuple[str, bytes, str]]],
    *,
    link_url: str | None = None,
) -> dict[str, Any]:
    data = {"link_url": link_url} if link_url is not None else {}
    response = await client.post(
        f"/api/v1/deliverables/{deliverable_id}/submissions",
        files=files,
        data=data,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def review(
    client: AsyncClient, deliverable_id: str, decision: str
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/deliverables/{deliverable_id}/reviews",
        json={"decision": decision},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def set_deadline(deliverable_id: str, deadline: datetime) -> None:
    async with SessionLocal() as db:
        deliverable = await db.get(Entregable, UUID(deliverable_id))
        assert deliverable is not None
        deliverable.fecha_limite = deadline
        await db.commit()


async def backdate_latest_submission(
    deliverable_id: str, submitted_at: datetime
) -> None:
    async with SessionLocal() as db:
        submission = await db.scalar(
            select(Entrega)
            .where(Entrega.entregable_id == UUID(deliverable_id))
            .order_by(Entrega.version.desc())
            .limit(1)
        )
        assert submission is not None
        submission.fecha_envio = submitted_at
        await db.commit()


async def setup_project(
    client: AsyncClient,
) -> tuple[
    Usuario,
    Usuario,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, student.correo)
    milestone = await create_milestone(client, str(project["id"]))
    deliverable = await create_deliverable(client, str(milestone["id"]))
    return professor, student, project, milestone, deliverable


async def test_create_deliverable_and_project_detail(
    client: AsyncClient,
) -> None:
    professor, student, project, milestone, deliverable = await setup_project(client)

    assert deliverable["title"] == "Entregable de prueba"
    assert deliverable["status"] == "pending"
    assert deliverable["my_role"] == "manager"
    assert deliverable["allowed_formats"] == ["pdf", "zip"]
    assert deliverable["version_count"] == 0
    assert deliverable["latest_submission"] is None
    assert deliverable["review"] is None
    assert len(deliverable["messages"]) == 1
    assert deliverable["messages"][0]["kind"] == "system"
    assert deliverable["messages"][0]["author_id"] is None
    assert deliverable["messages"][0]["author_name"] is None
    assert deliverable["messages"][0]["body"].endswith("ha creado el entregable.")

    project_detail = await client.get(f"/api/v1/projects/{project['id']}")
    assert project_detail.status_code == 200
    milestones = project_detail.json()["milestones"]
    assert len(milestones) == 1
    deliverables = milestones[0]["deliverables"]
    assert len(deliverables) == 1
    assert deliverables[0]["id"] == deliverable["id"]
    assert deliverables[0]["status"] == "pending"
    assert deliverables[0]["is_overdue"] is False
    assert deliverables[0]["latest_submission"] is None

    await login(client, student.correo)
    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["my_role"] == "collaborator"
    assert professor.correo != student.correo
    assert milestone["id"] == deliverable["milestone_id"]


async def test_create_deliverable_requires_manager(
    client: AsyncClient,
) -> None:
    _, student, _, milestone, _ = await setup_project(client)
    await login(client, student.correo)

    response = await client.post(
        f"/api/v1/milestones/{milestone['id']}/deliverables",
        json={
            "title": "No permitido",
            "description": "Sin permiso",
            "deadline_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "allowed_formats": ["pdf"],
            "max_file_size_mb": 50,
        },
    )

    assert response.status_code == 403


async def test_create_deliverable_validations(client: AsyncClient) -> None:
    _, _, _, milestone, _ = await setup_project(client)

    empty_fields = await client.post(
        f"/api/v1/milestones/{milestone['id']}/deliverables",
        json={
            "title": "   ",
            "description": "   ",
            "deadline_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "allowed_formats": ["pdf"],
            "max_file_size_mb": 50,
        },
    )
    assert empty_fields.status_code == 422
    assert empty_fields.json()["error"]["message"] == (
        "Los campos no pueden estar vacíos."
    )

    past_deadline = await client.post(
        f"/api/v1/milestones/{milestone['id']}/deliverables",
        json={
            "title": "Fecha pasada",
            "description": "Descripción",
            "deadline_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "allowed_formats": ["pdf"],
            "max_file_size_mb": 50,
        },
    )
    assert past_deadline.status_code == 422
    assert past_deadline.json()["error"]["message"] == (
        "Ingrese una fecha de entrega válida."
    )

    no_formats = await client.post(
        f"/api/v1/milestones/{milestone['id']}/deliverables",
        json={
            "title": "Sin formatos",
            "description": "Descripción",
            "deadline_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "allowed_formats": [],
            "max_file_size_mb": 50,
        },
    )
    assert no_formats.status_code == 422


async def test_edit_deliverable_and_past_deadline_rules(
    client: AsyncClient,
) -> None:
    _, _, _, _, deliverable = await setup_project(client)
    future = datetime.now(UTC) + timedelta(days=20)

    response = await client.patch(
        f"/api/v1/deliverables/{deliverable['id']}",
        json={
            "title": "Entregable editado",
            "description": "Descripción editada",
            "deadline_at": future.isoformat(),
            "allowed_formats": ["pdf"],
            "max_file_size_mb": 10,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Entregable editado"
    assert response.json()["allowed_formats"] == ["pdf"]

    changed_past = await client.patch(
        f"/api/v1/deliverables/{deliverable['id']}",
        json={
            "title": "Entregable editado",
            "description": "Descripción editada",
            "deadline_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "allowed_formats": ["pdf"],
            "max_file_size_mb": 10,
        },
    )
    assert changed_past.status_code == 422

    past_deadline = datetime.now(UTC) - timedelta(days=2)
    await set_deadline(str(deliverable["id"]), past_deadline)
    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.status_code == 200

    unchanged_past = await client.patch(
        f"/api/v1/deliverables/{deliverable['id']}",
        json={
            "title": "Entregable editado",
            "description": "Descripción con fecha vencida sin cambiar",
            "deadline_at": detail.json()["deadline_at"],
            "allowed_formats": ["pdf"],
            "max_file_size_mb": 10,
        },
    )
    assert unchanged_past.status_code == 200, unchanged_past.text
    assert "fecha vencida" in unchanged_past.json()["description"]


async def test_submissions_history_and_link(client: AsyncClient) -> None:
    _, student, _, _, deliverable = await setup_project(client)
    await login(client, student.correo)

    first = await upload(
        client,
        str(deliverable["id"]),
        [("files", ("v1.pdf", PDF_BYTES, "application/pdf"))],
        link_url="https://example.com/entrega-v1",
    )
    assert first["version"] == 1
    assert first["link_url"] == "https://example.com/entrega-v1"
    assert len(first["files"]) == 1

    second = await upload(
        client,
        str(deliverable["id"]),
        [("files", ("v2.pdf", PDF_BYTES + b"v2", "application/pdf"))],
    )
    assert second["version"] == 2
    assert second["link_url"] is None

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "submitted"
    assert detail.json()["version_count"] == 2
    assert detail.json()["latest_submission"]["version"] == 2

    await login(client, "professor@example.com")
    history = await client.get(f"/api/v1/deliverables/{deliverable['id']}/submissions")
    assert history.status_code == 200
    versions = history.json()
    assert [item["version"] for item in versions] == [1, 2]
    assert versions[0]["review"] is None

    await login(client, student.correo)
    forbidden_history = await client.get(
        f"/api/v1/deliverables/{deliverable['id']}/submissions"
    )
    assert forbidden_history.status_code == 403


async def test_link_only_submission(client: AsyncClient) -> None:
    _, student, _, _, deliverable = await setup_project(client)
    await login(client, student.correo)

    response = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        data={"link_url": "https://example.com/entrega-solo-enlace"},
    )
    assert response.status_code == 201, response.text
    submission = response.json()
    assert submission["version"] == 1
    assert submission["files"] == []
    assert submission["link_url"] == "https://example.com/entrega-solo-enlace"

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "submitted"
    assert detail.json()["latest_submission"]["files"] == []
    assert (
        detail.json()["latest_submission"]["link_url"]
        == "https://example.com/entrega-solo-enlace"
    )

    await login(client, "professor@example.com")
    history = await client.get(f"/api/v1/deliverables/{deliverable['id']}/submissions")
    assert history.status_code == 200
    assert history.json()[0]["files"] == []
    assert history.json()[0]["link_url"] == "https://example.com/entrega-solo-enlace"


async def test_submission_requires_file_or_link(client: AsyncClient) -> None:
    _, student, _, _, deliverable = await setup_project(client)
    await login(client, student.correo)

    empty = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        data={"link_url": "   "},
    )
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "NO_FILES_OR_LINK"
    assert empty.json()["error"]["message"] == (
        "Adjunta al menos un archivo o ingresa un enlace HTTPS válido."
    )

    invalid_link = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        data={"link_url": "http://example.com/entrega"},
    )
    assert invalid_link.status_code == 422
    assert invalid_link.json()["error"]["code"] == "INVALID_LINK"
    assert invalid_link.json()["error"]["message"] == (
        "Ingrese un enlace HTTPS válido."
    )


async def test_upload_validations(client: AsyncClient) -> None:
    _, student, _, milestone, deliverable = await setup_project(client)
    small = await create_deliverable(
        client,
        str(milestone["id"]),
        title="Entregable pequeño",
        max_file_size_mb=1,
    )
    await login(client, student.correo)

    invalid_format = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        files=[("files", ("malware.exe", b"x", "application/x-msdownload"))],
    )
    assert invalid_format.status_code == 422
    assert "no está permitido" in invalid_format.json()["error"]["message"]

    invalid_file_with_link = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        files=[("files", ("malware.exe", b"x", "application/x-msdownload"))],
        data={"link_url": "https://example.com/entrega-valida"},
    )
    assert invalid_file_with_link.status_code == 422
    assert "no está permitido" in invalid_file_with_link.json()["error"]["message"]

    empty_file = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        files=[("files", ("empty.pdf", b"", "application/pdf"))],
    )
    assert empty_file.status_code == 422
    assert "está vacío" in empty_file.json()["error"]["message"]

    too_large = await client.post(
        f"/api/v1/deliverables/{small['id']}/submissions",
        files=[
            (
                "files",
                ("big.pdf", b"x" * (1024 * 1024 + 1), "application/pdf"),
            )
        ],
    )
    assert too_large.status_code == 422
    assert "supera el tamaño máximo" in too_large.json()["error"]["message"]

    invalid_link = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        files=[("files", ("v1.pdf", PDF_BYTES, "application/pdf"))],
        data={"link_url": "http://example.com/entrega"},
    )
    assert invalid_link.status_code == 422
    assert invalid_link.json()["error"]["message"] == (
        "Ingrese un enlace HTTPS válido."
    )

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.json()["status"] == "pending"
    assert detail.json()["version_count"] == 0

    await login(client, "professor@example.com")
    manager_upload = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        files=[("files", ("manager.pdf", PDF_BYTES, "application/pdf"))],
    )
    assert manager_upload.status_code == 403


async def test_review_state_machine(client: AsyncClient) -> None:
    _, student, project, _, deliverable = await setup_project(client)
    await login(client, student.correo)
    await upload(
        client,
        str(deliverable["id"]),
        [("files", ("v1.pdf", PDF_BYTES, "application/pdf"))],
    )

    await login(client, "professor@example.com")
    changes = await review(client, str(deliverable["id"]), "changes_requested")
    assert changes["decision"] == "changes_requested"

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.json()["status"] == "changes_requested"
    assert detail.json()["review"]["decision"] == "changes_requested"

    await login(client, student.correo)
    await upload(
        client,
        str(deliverable["id"]),
        [("files", ("v2.pdf", PDF_BYTES + b"v2", "application/pdf"))],
    )

    await login(client, "professor@example.com")
    approved = await review(client, str(deliverable["id"]), "approved")
    assert approved["decision"] == "approved"

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.json()["status"] == "approved"
    assert detail.json()["review"]["decision"] == "approved"

    project_detail = await client.get(f"/api/v1/projects/{project['id']}")
    summary = project_detail.json()["milestones"][0]["deliverables"][0]
    assert summary["status"] == "approved"
    assert summary["latest_submission"]["version"] == 2
    assert summary["review"]["decision"] == "approved"

    await login(client, student.correo)
    after_approval = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        files=[("files", ("v3.pdf", PDF_BYTES, "application/pdf"))],
    )
    assert after_approval.status_code == 409

    await login(client, "professor@example.com")
    review_after_approval = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/reviews",
        json={"decision": "approved"},
    )
    assert review_after_approval.status_code == 409


async def test_deliverable_lifecycle_forum_events(client: AsyncClient) -> None:
    _, student, _, _, deliverable = await setup_project(client)

    edited = await client.patch(
        f"/api/v1/deliverables/{deliverable['id']}",
        json={
            "title": "Entregable editado",
            "description": "Descripción editada",
            "deadline_at": deliverable["deadline_at"],
            "allowed_formats": deliverable["allowed_formats"],
            "max_file_size_mb": deliverable["max_file_size_mb"],
        },
    )
    assert edited.status_code == 200, edited.text

    await login(client, student.correo)
    await upload(
        client,
        str(deliverable["id"]),
        [("files", ("v1.pdf", PDF_BYTES, "application/pdf"))],
    )

    await login(client, "professor@example.com")
    await review(client, str(deliverable["id"]), "approved")

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [message["kind"] for message in messages] == ["system"] * 4
    assert all(message["author_id"] is None for message in messages)
    assert all(message["author_name"] is None for message in messages)
    assert messages[0]["body"].endswith("ha creado el entregable.")
    assert messages[1]["body"].endswith("ha editado el entregable.")
    assert messages[2]["body"].endswith("ha entregado la versión 1.")
    assert messages[3]["body"].endswith("ha marcado la versión 1 como Aprobada.")


async def test_review_requires_submission_and_manager(
    client: AsyncClient,
) -> None:
    _, student, _, _, deliverable = await setup_project(client)

    before_submission = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/reviews",
        json={"decision": "approved"},
    )
    assert before_submission.status_code == 409

    await login(client, student.correo)
    collaborator_review = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/reviews",
        json={"decision": "approved"},
    )
    assert collaborator_review.status_code == 403


async def test_overdue_flow(client: AsyncClient) -> None:
    _, student, _, _, deliverable = await setup_project(client)
    await set_deadline(
        str(deliverable["id"]),
        datetime.now(UTC) - timedelta(days=2),
    )

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["is_overdue"] is True

    await login(client, student.correo)
    await upload(
        client,
        str(deliverable["id"]),
        [("files", ("late.pdf", PDF_BYTES, "application/pdf"))],
    )
    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.json()["status"] == "submitted"
    assert detail.json()["is_overdue"] is True

    await login(client, "professor@example.com")
    await review(client, str(deliverable["id"]), "approved")
    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.json()["status"] == "approved"
    assert detail.json()["is_overdue"] is False


async def test_on_time_submission_prevents_overdue(
    client: AsyncClient,
) -> None:
    _, student, _, _, deliverable = await setup_project(client)
    await login(client, student.correo)
    await upload(
        client,
        str(deliverable["id"]),
        [("files", ("on-time.pdf", PDF_BYTES, "application/pdf"))],
    )
    now = datetime.now(UTC)
    await backdate_latest_submission(str(deliverable["id"]), now - timedelta(days=2))
    await set_deadline(str(deliverable["id"]), now - timedelta(days=1))

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "submitted"
    assert detail.json()["is_overdue"] is False


async def test_project_list_counts_overdue_and_review(
    client: AsyncClient,
) -> None:
    professor, student, project, _, deliverable = await setup_project(client)
    await set_deadline(
        str(deliverable["id"]),
        datetime.now(UTC) - timedelta(days=1),
    )

    listing = await client.get("/api/v1/projects")
    assert listing.status_code == 200
    item = listing.json()[0]
    assert item["total_deliverables"] == 1
    assert item["approved_deliverables"] == 0
    assert item["overdue_deliverables"] == 1
    assert item["pending_review_deliverables"] == 0
    assert item["id"] == project["id"]

    await login(client, student.correo)
    await upload(
        client,
        str(deliverable["id"]),
        [("files", ("late.pdf", PDF_BYTES, "application/pdf"))],
    )

    await login(client, professor.correo)
    item = (await client.get("/api/v1/projects")).json()[0]
    assert item["pending_review_deliverables"] == 1
    assert item["overdue_deliverables"] == 1

    await review(client, str(deliverable["id"]), "approved")
    item = (await client.get("/api/v1/projects")).json()[0]
    assert item["approved_deliverables"] == 1
    assert item["overdue_deliverables"] == 0
    assert item["pending_review_deliverables"] == 0


async def test_pending_reviews_endpoint(client: AsyncClient) -> None:
    professor, student, project, milestone, deliverable = await setup_project(client)

    empty = await client.get("/api/v1/reviews/pending")
    assert empty.status_code == 200
    assert empty.json() == []

    await login(client, student.correo)
    await upload(
        client,
        str(deliverable["id"]),
        [("files", ("v1.pdf", PDF_BYTES, "application/pdf"))],
    )
    collaborator_pending = await client.get("/api/v1/reviews/pending")
    assert collaborator_pending.status_code == 200
    assert collaborator_pending.json() == []

    await login(client, professor.correo)
    pending = await client.get("/api/v1/reviews/pending")
    assert pending.status_code == 200
    items = pending.json()
    assert len(items) == 1
    assert items[0]["deliverable_id"] == deliverable["id"]
    assert items[0]["title"] == "Entregable de prueba"
    assert items[0]["project_id"] == project["id"]
    assert items[0]["project_topic"] == "Proyecto de entregables"
    assert items[0]["milestone_name"] == milestone["name"]
    assert items[0]["collaborator_name"] == "Student"
    assert items[0]["version"] == 1

    await review(client, str(deliverable["id"]), "approved")
    pending_after_review = await client.get("/api/v1/reviews/pending")
    assert pending_after_review.json() == []


async def test_file_download_permissions(client: AsyncClient) -> None:
    _, student, _, _, deliverable = await setup_project(client)
    await login(client, student.correo)
    first = await upload(
        client,
        str(deliverable["id"]),
        [("files", ("v1.pdf", b"version-1", "application/pdf"))],
    )
    second = await upload(
        client,
        str(deliverable["id"]),
        [("files", ("v2.pdf", b"version-2", "application/pdf"))],
    )
    first_file = first["files"][0]["id"]
    second_file = second["files"][0]["id"]

    await login(client, "professor@example.com")
    manager_first = await client.get(f"/api/v1/files/{first_file}/download")
    assert manager_first.status_code == 200
    assert manager_first.content == b"version-1"
    manager_second = await client.get(f"/api/v1/files/{second_file}/download")
    assert manager_second.status_code == 200
    assert manager_second.content == b"version-2"

    await login(client, student.correo)
    collaborator_first = await client.get(f"/api/v1/files/{first_file}/download")
    assert collaborator_first.status_code == 403
    collaborator_second = await client.get(f"/api/v1/files/{second_file}/download")
    assert collaborator_second.status_code == 200
    assert collaborator_second.content == b"version-2"

    outsider = await create_user("outsider@example.com")
    await login(client, outsider.correo)
    outsider_download = await client.get(f"/api/v1/files/{second_file}/download")
    assert outsider_download.status_code == 404


async def test_forum_messages(client: AsyncClient) -> None:
    _, student, _, _, deliverable = await setup_project(client)
    await login(client, student.correo)

    first = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/messages",
        json={"body": "Primer mensaje"},
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/messages",
        json={"body": "Segundo mensaje"},
    )
    assert second.status_code == 201, second.text

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    messages = detail.json()["messages"]
    assert [message["kind"] for message in messages] == [
        "system",
        "user",
        "user",
    ]
    assert messages[0]["body"].endswith("ha creado el entregable.")
    assert [message["body"] for message in messages[1:]] == [
        "Primer mensaje",
        "Segundo mensaje",
    ]
    assert all(message["author_name"] is not None for message in messages[1:])

    empty = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/messages",
        json={"body": "   "},
    )
    assert empty.status_code == 422
    assert empty.json()["error"]["message"] == ("El comentario no puede estar vacío.")

    await login(client, "professor@example.com")
    manager_detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert len(manager_detail.json()["messages"]) == 3

    outsider = await create_user("outsider@example.com")
    await login(client, outsider.correo)
    forbidden = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/messages",
        json={"body": "No permitido"},
    )
    assert forbidden.status_code == 404


async def test_non_participant_cannot_access_deliverable(
    client: AsyncClient,
) -> None:
    _, _, _, _, deliverable = await setup_project(client)
    outsider = await create_user("outsider@example.com")
    await login(client, outsider.correo)

    detail = await client.get(f"/api/v1/deliverables/{deliverable['id']}")
    assert detail.status_code == 404

    history = await client.get(f"/api/v1/deliverables/{deliverable['id']}/submissions")
    assert history.status_code == 404

    upload_response = await client.post(
        f"/api/v1/deliverables/{deliverable['id']}/submissions",
        files=[("files", ("v1.pdf", PDF_BYTES, "application/pdf"))],
    )
    assert upload_response.status_code == 404
