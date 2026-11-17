from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient, Response

from app.db.session import SessionLocal
from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Usuario
from app.modules.auth.security import hash_password

PASSWORD = "TestPassword123!"
PDF_BYTES = b"%PDF-1.4\ncontenido de prueba\n"
ZIP_BYTES = b"PK\x03\x04contenido de prueba"
DOCX_BYTES = b"PK\x03\x04contenido de prueba docx"
FileUpload = tuple[str, tuple[str, bytes, str]]


@dataclass(frozen=True)
class UploadScenario:
    """Datos mínimos para probar una subida."""

    professor: Usuario
    student: Usuario
    project: dict[str, Any]
    milestone: dict[str, Any]
    deliverable: dict[str, Any]


@dataclass(frozen=True)
class RbacScenario:
    """Proyecto compartido por gestor, colaborador y usuario ajeno."""

    manager: Usuario
    collaborator: Usuario
    outsider: Usuario
    project: dict[str, Any]
    milestone: dict[str, Any]
    pending_deliverable: dict[str, Any]
    submitted_deliverable: dict[str, Any]
    submission: dict[str, Any]
    file_id: str


async def create_user(
    email: str,
    *,
    user_type: UserType = UserType.PROFESSOR,
) -> Usuario:
    """Crea una cuenta activa con una contraseña conocida."""
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
    """Inicia sesión y falla si el backend no acepta las credenciales."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text


async def create_project(
    client: AsyncClient,
    *,
    collaborator_emails: list[str],
    manager_emails: list[str] | None = None,
    topic: str = "Proyecto NFR",
) -> dict[str, Any]:
    """Crea un proyecto y devuelve su representación de la API."""
    response = await client.post(
        "/api/v1/projects",
        json={
            "topic": topic,
            "project_type": "memoir",
            "manager_emails": manager_emails or [],
            "collaborator_emails": collaborator_emails,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_milestone(
    client: AsyncClient,
    project_id: str,
    *,
    name: str = "Hito NFR",
    position: int = 1,
) -> dict[str, Any]:
    """Crea un hito y devuelve su representación de la API."""
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
    title: str = "Entregable NFR",
    deadline: datetime | None = None,
    formats: list[str] | None = None,
    max_file_size_mb: int = 50,
) -> dict[str, Any]:
    """Crea un entregable y devuelve su representación de la API."""
    due = deadline or (datetime.now(UTC) + timedelta(days=10))
    response = await client.post(
        f"/api/v1/milestones/{milestone_id}/deliverables",
        json={
            "title": title,
            "description": "Descripción del entregable NFR",
            "deadline_at": due.isoformat(),
            "allowed_formats": formats or ["pdf", "zip", "docx"],
            "max_file_size_mb": max_file_size_mb,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def post_submission(
    client: AsyncClient,
    deliverable_id: str,
    *,
    files: list[FileUpload] | None = None,
    link_url: str | None = None,
) -> Response:
    """Envía una entrega sin imponer el código de respuesta."""
    data = {"link_url": link_url} if link_url is not None else {}
    return await client.post(
        f"/api/v1/deliverables/{deliverable_id}/submissions",
        files=files or [],
        data=data,
    )


async def submit(
    client: AsyncClient,
    deliverable_id: str,
    *,
    files: list[FileUpload] | None = None,
    link_url: str | None = None,
) -> dict[str, Any]:
    """Envía una entrega válida y devuelve su representación de la API."""
    response = await post_submission(
        client,
        deliverable_id,
        files=files,
        link_url=link_url,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def post_review(
    client: AsyncClient,
    deliverable_id: str,
    decision: str,
    *,
    files: list[FileUpload] | None = None,
) -> Response:
    """Registra una revisión sin imponer el código de respuesta."""
    return await client.post(
        f"/api/v1/deliverables/{deliverable_id}/reviews",
        data={"decision": decision},
        files=files or [],
    )


async def review(
    client: AsyncClient,
    deliverable_id: str,
    decision: str,
    *,
    files: list[FileUpload] | None = None,
) -> dict[str, Any]:
    """Registra una revisión válida y devuelve su representación de la API."""
    response = await post_review(
        client,
        deliverable_id,
        decision,
        files=files,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def setup_upload_scenario(
    client: AsyncClient,
    *,
    formats: list[str] | None = None,
    max_file_size_mb: int = 50,
) -> UploadScenario:
    """Crea un proyecto con un entregable listo para recibir archivos."""
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, collaborator_emails=[student.correo])
    milestone = await create_milestone(client, str(project["id"]))
    deliverable = await create_deliverable(
        client,
        str(milestone["id"]),
        formats=formats,
        max_file_size_mb=max_file_size_mb,
    )
    return UploadScenario(
        professor=professor,
        student=student,
        project=project,
        milestone=milestone,
        deliverable=deliverable,
    )


async def setup_rbac_scenario(client: AsyncClient) -> RbacScenario:
    """Crea un proyecto con participantes de cada rol y una entrega inicial."""
    manager = await create_user("manager@example.com")
    collaborator = await create_user(
        "collaborator@example.com", user_type=UserType.STUDENT
    )
    outsider = await create_user("outsider@example.com", user_type=UserType.STUDENT)

    await login(client, manager.correo)
    project = await create_project(client, collaborator_emails=[collaborator.correo])
    milestone = await create_milestone(client, str(project["id"]))
    pending_deliverable = await create_deliverable(
        client,
        str(milestone["id"]),
        title="Entregable pendiente",
    )
    submitted_deliverable = await create_deliverable(
        client,
        str(milestone["id"]),
        title="Entregable entregado",
    )

    await login(client, collaborator.correo)
    submission = await submit(
        client,
        str(submitted_deliverable["id"]),
        files=[("files", ("v1.pdf", PDF_BYTES, "application/pdf"))],
    )
    file_id = str(submission["files"][0]["id"])

    return RbacScenario(
        manager=manager,
        collaborator=collaborator,
        outsider=outsider,
        project=project,
        milestone=milestone,
        pending_deliverable=pending_deliverable,
        submitted_deliverable=submitted_deliverable,
        submission=submission,
        file_id=file_id,
    )
