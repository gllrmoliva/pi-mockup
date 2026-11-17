import pytest
from httpx import AsyncClient

from tests.nfr_helpers import (
    DOCX_BYTES,
    PDF_BYTES,
    ZIP_BYTES,
    FileUpload,
    UploadScenario,
    create_user,
    login,
    post_review,
    review,
    setup_upload_scenario,
    submit,
)

pytestmark = pytest.mark.nfr

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


async def _submitted_scenario(
    client: AsyncClient,
    *,
    formats: list[str] | None = None,
    max_file_size_mb: int = 50,
) -> UploadScenario:
    """Crea un entregable con una entrega válida y deja al gestor autenticado."""
    scenario = await setup_upload_scenario(
        client,
        formats=formats,
        max_file_size_mb=max_file_size_mb,
    )
    await login(client, scenario.student.correo)
    await submit(
        client,
        str(scenario.deliverable["id"]),
        files=[("files", ("v1.pdf", PDF_BYTES, "application/pdf"))],
    )
    await login(client, scenario.professor.correo)
    return scenario


@pytest.mark.parametrize(
    ("files", "expected_names"),
    [
        pytest.param(
            [("files", ("correccion.pdf", PDF_BYTES + b"r", "application/pdf"))],
            {"correccion.pdf"},
            id="pdf",
        ),
        pytest.param(
            [("files", ("anexos.zip", ZIP_BYTES + b"r", "application/zip"))],
            {"anexos.zip"},
            id="zip",
        ),
        pytest.param(
            [("files", ("correccion.docx", DOCX_BYTES + b"r", DOCX_MIME))],
            {"correccion.docx"},
            id="docx",
        ),
        pytest.param(
            [
                ("files", ("correccion.pdf", PDF_BYTES + b"r1", "application/pdf")),
                ("files", ("anexos.zip", ZIP_BYTES + b"r2", "application/zip")),
            ],
            {"correccion.pdf", "anexos.zip"},
            id="multiple-files",
        ),
    ],
)
async def test_allowed_review_file_formats(
    client: AsyncClient,
    files: list[FileUpload],
    expected_names: set[str],
) -> None:
    scenario = await _submitted_scenario(
        client,
        formats=["pdf", "zip", "docx"],
    )

    response = await post_review(
        client,
        str(scenario.deliverable["id"]),
        "approved",
        files=files,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert {uploaded["original_name"] for uploaded in body["files"]} == expected_names
    for uploaded in body["files"]:
        assert uploaded["size_bytes"] > 0
        assert len(uploaded["sha256"]) == 64

    detail = await client.get(f"/api/v1/deliverables/{scenario.deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["version_count"] == 1
    assert {file["original_name"] for file in detail.json()["review"]["files"]} == (
        expected_names
    )

    history = await client.get(
        f"/api/v1/deliverables/{scenario.deliverable['id']}/submissions"
    )
    assert history.status_code == 200
    assert {file["original_name"] for file in history.json()[0]["review"]["files"]} == (
        expected_names
    )


@pytest.mark.parametrize(
    ("files", "expected_code"),
    [
        pytest.param(
            [("files", ("correccion.exe", b"x", "application/x-msdownload"))],
            "INVALID_FILE_FORMAT",
            id="disallowed-extension",
        ),
        pytest.param(
            [("files", ("correccion.pdf", PDF_BYTES, "application/zip"))],
            "INVALID_FILE_FORMAT",
            id="mime-mismatch",
        ),
        pytest.param(
            [("files", ("correccion.pdf", PDF_BYTES, ""))],
            "INVALID_FILE_FORMAT",
            id="missing-mime",
        ),
        pytest.param(
            [("files", ("vacio.pdf", b"", "application/pdf"))],
            "EMPTY_FILE",
            id="empty-file",
        ),
        pytest.param(
            [
                (
                    "files",
                    ("grande.pdf", b"x" * (1024 * 1024 + 1), "application/pdf"),
                )
            ],
            "FILE_TOO_LARGE",
            id="too-large",
        ),
        pytest.param(
            [
                ("files", ("correcto.pdf", PDF_BYTES, "application/pdf")),
                ("files", ("malware.exe", b"x", "application/x-msdownload")),
            ],
            "INVALID_FILE_FORMAT",
            id="valid-and-invalid-file",
        ),
    ],
)
async def test_rejected_review_files_are_atomic(
    client: AsyncClient,
    files: list[FileUpload],
    expected_code: str,
) -> None:
    scenario = await _submitted_scenario(client, max_file_size_mb=1)

    response = await post_review(
        client,
        str(scenario.deliverable["id"]),
        "changes_requested",
        files=files,
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == expected_code

    detail = await client.get(f"/api/v1/deliverables/{scenario.deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "submitted"
    assert detail.json()["review"] is None

    history = await client.get(
        f"/api/v1/deliverables/{scenario.deliverable['id']}/submissions"
    )
    assert history.status_code == 200
    assert history.json()[0]["review"] is None


async def test_review_file_metadata_event_and_download_permissions(
    client: AsyncClient,
) -> None:
    scenario = await _submitted_scenario(client, formats=["pdf"])
    payload = PDF_BYTES + b"revision"

    reviewed = await review(
        client,
        str(scenario.deliverable["id"]),
        "approved",
        files=[("files", ("correccion.pdf", payload, "application/pdf"))],
    )
    assert len(reviewed["files"]) == 1
    uploaded = reviewed["files"][0]
    assert uploaded["original_name"] == "correccion.pdf"
    assert uploaded["mime_type"] == "application/pdf"
    assert uploaded["size_bytes"] == len(payload)
    assert len(uploaded["sha256"]) == 64

    detail = await client.get(f"/api/v1/deliverables/{scenario.deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["messages"][-1]["body"].endswith(
        "ha marcado la versión 1 como Aprobada y adjuntó 1 archivo."
    )

    manager_download = await client.get(f"/api/v1/files/{uploaded['id']}/download")
    assert manager_download.status_code == 200
    assert manager_download.content == payload

    await login(client, scenario.student.correo)
    collaborator_download = await client.get(f"/api/v1/files/{uploaded['id']}/download")
    assert collaborator_download.status_code == 200

    outsider = await create_user("review-outsider@example.com")
    await login(client, outsider.correo)
    outsider_download = await client.get(f"/api/v1/files/{uploaded['id']}/download")
    assert outsider_download.status_code == 404


async def test_collaborator_cannot_download_old_review_files(
    client: AsyncClient,
) -> None:
    scenario = await _submitted_scenario(client)
    first_review = await review(
        client,
        str(scenario.deliverable["id"]),
        "changes_requested",
        files=[
            (
                "files",
                ("revision-v1.pdf", PDF_BYTES + b"review-v1", "application/pdf"),
            )
        ],
    )
    first_file_id = first_review["files"][0]["id"]

    await login(client, scenario.student.correo)
    await submit(
        client,
        str(scenario.deliverable["id"]),
        files=[("files", ("v2.pdf", PDF_BYTES + b"v2", "application/pdf"))],
    )

    await login(client, scenario.professor.correo)
    second_review = await review(
        client,
        str(scenario.deliverable["id"]),
        "approved",
        files=[
            (
                "files",
                ("revision-v2.pdf", PDF_BYTES + b"review-v2", "application/pdf"),
            )
        ],
    )
    second_file_id = second_review["files"][0]["id"]

    for file_id in (first_file_id, second_file_id):
        manager_download = await client.get(f"/api/v1/files/{file_id}/download")
        assert manager_download.status_code == 200

    await login(client, scenario.student.correo)
    old_review_download = await client.get(f"/api/v1/files/{first_file_id}/download")
    assert old_review_download.status_code == 403

    latest_review_download = await client.get(
        f"/api/v1/files/{second_file_id}/download"
    )
    assert latest_review_download.status_code == 200
