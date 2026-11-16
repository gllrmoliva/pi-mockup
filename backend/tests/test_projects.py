from typing import Any, cast

from httpx import AsyncClient

from app.db.session import SessionLocal
from app.modules.auth.enums import UserStatus, UserType
from app.modules.auth.models import Usuario
from app.modules.auth.security import hash_password

PASSWORD = "TestPassword123!"


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
    client: AsyncClient,
    *,
    topic: str = "Proyecto de prueba",
    project_type: str = "memoir",
    manager_emails: list[str] | None = None,
    collaborator_emails: list[str] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/projects",
        json={
            "topic": topic,
            "project_type": project_type,
            "manager_emails": manager_emails or [],
            "collaborator_emails": collaborator_emails or [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def roles_by_email(project: dict[str, Any]) -> dict[str, str]:
    participants = project["participants"]
    assert isinstance(participants, list)
    roles: dict[str, str] = {}
    for participant in cast(list[dict[str, Any]], participants):
        roles[str(participant["email"])] = str(participant["role"])
    return roles


async def test_create_project_creator_is_manager_and_listed(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)

    project = await create_project(
        client,
        topic="Reconocimiento de gestos",
        collaborator_emails=[student.correo],
    )

    assert project["topic"] == "Reconocimiento de gestos"
    assert project["project_type"] == "memoir"
    assert project["status"] == "active"
    assert project["my_role"] == "manager"
    assert project["milestones"] == []
    assert roles_by_email(project) == {
        professor.correo: "manager",
        student.correo: "collaborator",
    }

    listing = await client.get("/api/v1/projects")
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    assert items[0]["id"] == project["id"]
    assert items[0]["my_role"] == "manager"
    assert items[0]["total_deliverables"] == 0
    assert items[0]["next_deadline_at"] is None

    detail = await client.get(f"/api/v1/projects/{project['id']}")
    assert detail.status_code == 200
    assert detail.json()["milestones"] == []


async def test_create_project_requires_professor(client: AsyncClient) -> None:
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, student.correo)

    response = await client.post(
        "/api/v1/projects",
        json={
            "topic": "Proyecto de estudiante",
            "project_type": "memoir",
            "manager_emails": [],
            "collaborator_emails": [student.correo],
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == (
        "Solo un profesor puede crear proyectos."
    )


async def test_create_project_requires_collaborator(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    await login(client, professor.correo)

    response = await client.post(
        "/api/v1/projects",
        json={
            "topic": "Proyecto sin colaboradores",
            "project_type": "memoir",
            "manager_emails": [],
            "collaborator_emails": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == (
        "El proyecto requiere tener al menos un colaborador."
    )


async def test_create_project_rejects_unknown_email(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    await login(client, professor.correo)

    response = await client.post(
        "/api/v1/projects",
        json={
            "topic": "Proyecto con correo desconocido",
            "project_type": "memoir",
            "manager_emails": [],
            "collaborator_emails": ["missing@example.com"],
        },
    )

    assert response.status_code == 422
    assert "No existe una cuenta activa" in response.json()["error"]["message"]


async def test_create_project_rejects_duplicate_roles(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)

    response = await client.post(
        "/api/v1/projects",
        json={
            "topic": "Proyecto con roles duplicados",
            "project_type": "memoir",
            "manager_emails": [student.correo],
            "collaborator_emails": [student.correo],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == (
        "Un usuario no puede tener dos roles en el mismo proyecto."
    )


async def test_create_project_with_second_manager(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    co_manager = await create_user("co.manager@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)

    project = await create_project(
        client,
        manager_emails=[co_manager.correo],
        collaborator_emails=[student.correo],
    )

    assert roles_by_email(project) == {
        professor.correo: "manager",
        co_manager.correo: "manager",
        student.correo: "collaborator",
    }


async def test_create_milestones_and_shift_positions(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, collaborator_emails=[student.correo])

    first = await client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        json={"name": "Primero", "position": 1},
    )
    assert first.status_code == 201, first.text
    assert first.json()["order_index"] == 1
    assert first.json()["deliverables"] == []

    second = await client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        json={"name": "Segundo", "position": 1},
    )
    assert second.status_code == 201, second.text

    detail = await client.get(f"/api/v1/projects/{project['id']}")
    assert detail.status_code == 200
    milestones = detail.json()["milestones"]
    assert [milestone["name"] for milestone in milestones] == [
        "Segundo",
        "Primero",
    ]
    assert [milestone["order_index"] for milestone in milestones] == [1, 2]


async def test_create_milestone_validation(client: AsyncClient) -> None:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, collaborator_emails=[student.correo])

    empty_name = await client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        json={"name": "   ", "position": 1},
    )
    assert empty_name.status_code == 422
    assert empty_name.json()["error"]["message"] == "El Hito debe tener un nombre."

    invalid_position = await client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        json={"name": "Fuera de rango", "position": 5},
    )
    assert invalid_position.status_code == 422
    assert invalid_position.json()["error"]["message"] == (
        "La posición del hito no es válida."
    )


async def test_create_milestone_requires_manager(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, collaborator_emails=[student.correo])

    await login(client, student.correo)
    response = await client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        json={"name": "No permitido", "position": 1},
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == (
        "Solo un gestor del proyecto puede realizar esta acción."
    )


async def test_edit_project_updates_fields_and_participants(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    co_manager = await create_user("co.manager@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, collaborator_emails=[student.correo])

    response = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={
            "topic": "Tema actualizado",
            "project_type": "thesis",
            "manager_emails": [professor.correo, co_manager.correo],
            "collaborator_emails": [student.correo],
        },
    )

    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["topic"] == "Tema actualizado"
    assert updated["project_type"] == "thesis"
    assert updated["my_role"] == "manager"
    assert roles_by_email(updated) == {
        professor.correo: "manager",
        co_manager.correo: "manager",
        student.correo: "collaborator",
    }

    detail = await client.get(f"/api/v1/projects/{project['id']}")
    assert detail.status_code == 200
    assert detail.json()["topic"] == "Tema actualizado"


async def test_edit_project_requires_manager(client: AsyncClient) -> None:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, collaborator_emails=[student.correo])

    await login(client, student.correo)
    response = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={
            "topic": "Tema no permitido",
            "project_type": "memoir",
            "manager_emails": [professor.correo],
            "collaborator_emails": [student.correo],
        },
    )

    assert response.status_code == 403


async def test_edit_project_requires_manager_and_collaborator(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, collaborator_emails=[student.correo])

    no_collaborator = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={
            "topic": "Sin colaboradores",
            "project_type": "memoir",
            "manager_emails": [professor.correo],
            "collaborator_emails": [],
        },
    )
    assert no_collaborator.status_code == 422
    assert no_collaborator.json()["error"]["message"] == (
        "El proyecto requiere tener al menos un colaborador."
    )

    no_manager = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={
            "topic": "Sin gestores",
            "project_type": "memoir",
            "manager_emails": [],
            "collaborator_emails": [student.correo],
        },
    )
    assert no_manager.status_code == 422
    assert no_manager.json()["error"]["message"] == (
        "El proyecto requiere tener al menos un gestor."
    )


async def test_edit_project_can_remove_current_manager(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    co_manager = await create_user("co.manager@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(
        client,
        manager_emails=[co_manager.correo],
        collaborator_emails=[student.correo],
    )

    response = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={
            "topic": "Proyecto transferido",
            "project_type": "memoir",
            "manager_emails": [co_manager.correo],
            "collaborator_emails": [student.correo],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["my_role"] is None

    detail = await client.get(f"/api/v1/projects/{project['id']}")
    assert detail.status_code == 404


async def test_non_participant_cannot_view_or_list_projects(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    outsider = await create_user("outsider@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)
    project = await create_project(client, collaborator_emails=[student.correo])

    await login(client, outsider.correo)
    listing = await client.get("/api/v1/projects")
    assert listing.status_code == 200
    assert listing.json() == []

    detail = await client.get(f"/api/v1/projects/{project['id']}")
    assert detail.status_code == 404


async def test_project_list_is_sorted_by_last_modification(
    client: AsyncClient,
) -> None:
    professor = await create_user("professor@example.com")
    student = await create_user("student@example.com", user_type=UserType.STUDENT)
    await login(client, professor.correo)

    first = await create_project(
        client,
        topic="Primer proyecto",
        collaborator_emails=[student.correo],
    )
    second = await create_project(
        client,
        topic="Segundo proyecto",
        collaborator_emails=[student.correo],
    )

    updated = await client.patch(
        f"/api/v1/projects/{first['id']}",
        json={
            "topic": "Primer proyecto actualizado",
            "project_type": "memoir",
            "manager_emails": [professor.correo],
            "collaborator_emails": [student.correo],
        },
    )
    assert updated.status_code == 200, updated.text

    listing = await client.get("/api/v1/projects")
    assert listing.status_code == 200
    items = listing.json()
    assert [item["id"] for item in items] == [first["id"], second["id"]]
