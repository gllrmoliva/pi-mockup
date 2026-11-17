import pytest
from httpx import AsyncClient

from tests.nfr_helpers import (
    DOCX_BYTES,
    PDF_BYTES,
    ZIP_BYTES,
    FileUpload,
    login,
    post_submission,
    setup_upload_scenario,
)

pytestmark = pytest.mark.nfr

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.mark.parametrize(
    ("files", "link_url", "expected_file_count"),
    [
        pytest.param(
            [("files", ("informe.pdf", PDF_BYTES, "application/pdf"))],
            None,
            1,
            id="pdf",
        ),
        pytest.param(
            [("files", ("anexos.zip", ZIP_BYTES, "application/zip"))],
            None,
            1,
            id="zip",
        ),
        pytest.param(
            [("files", ("anexos.zip", ZIP_BYTES, "application/x-zip-compressed"))],
            None,
            1,
            id="zip-alternate-mime",
        ),
        pytest.param(
            [("files", ("informe.docx", DOCX_BYTES, DOCX_MIME))],
            None,
            1,
            id="docx",
        ),
        pytest.param(
            [("files", ("INFORME.PDF", PDF_BYTES, "application/pdf"))],
            None,
            1,
            id="uppercase-extension",
        ),
        pytest.param(
            [
                ("files", ("informe.pdf", PDF_BYTES, "application/pdf")),
                ("files", ("anexos.zip", ZIP_BYTES, "application/zip")),
            ],
            None,
            2,
            id="multiple-files",
        ),
        pytest.param(
            [("files", ("informe.pdf", PDF_BYTES, "application/pdf"))],
            "https://example.com/entrega",
            1,
            id="file-and-link",
        ),
        pytest.param(
            None,
            "https://example.com/entrega",
            0,
            id="link-only",
        ),
    ],
)
async def test_allowed_upload_formats(
    client: AsyncClient,
    files: list[FileUpload] | None,
    link_url: str | None,
    expected_file_count: int,
) -> None:
    scenario = await setup_upload_scenario(client)
    await login(client, scenario.student.correo)

    response = await post_submission(
        client,
        str(scenario.deliverable["id"]),
        files=files,
        link_url=link_url,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == 1
    assert body["link_url"] == link_url
    assert len(body["files"]) == expected_file_count
    for uploaded_file in body["files"]:
        assert uploaded_file["size_bytes"] > 0
        assert len(uploaded_file["sha256"]) == 64


@pytest.mark.parametrize(
    ("files", "link_url", "expected_code"),
    [
        pytest.param(
            [("files", ("malware.exe", b"x", "application/x-msdownload"))],
            None,
            "INVALID_FILE_FORMAT",
            id="disallowed-extension",
        ),
        pytest.param(
            [("files", ("informe.pdf", PDF_BYTES, "application/zip"))],
            None,
            "INVALID_FILE_FORMAT",
            id="mime-mismatch",
        ),
        pytest.param(
            [("files", ("informe.pdf", PDF_BYTES, ""))],
            None,
            "INVALID_FILE_FORMAT",
            id="missing-mime",
        ),
        pytest.param(
            [("files", ("vacio.pdf", b"", "application/pdf"))],
            None,
            "EMPTY_FILE",
            id="empty-file",
        ),
        pytest.param(
            [("files", ("grande.pdf", b"x" * (1024 * 1024 + 1), "application/pdf"))],
            None,
            "FILE_TOO_LARGE",
            id="too-large",
        ),
        pytest.param(
            None,
            None,
            "NO_FILES_OR_LINK",
            id="no-files-or-link",
        ),
        pytest.param(
            [("files", ("informe.pdf", PDF_BYTES, "application/pdf"))],
            "http://example.com/entrega",
            "INVALID_LINK",
            id="non-https-link",
        ),
        pytest.param(
            [("files", ("malware.exe", b"x", "application/x-msdownload"))],
            "https://example.com/entrega",
            "INVALID_FILE_FORMAT",
            id="invalid-file-with-valid-link",
        ),
    ],
)
async def test_rejected_uploads_are_atomic(
    client: AsyncClient,
    files: list[FileUpload] | None,
    link_url: str | None,
    expected_code: str,
) -> None:
    scenario = await setup_upload_scenario(client, max_file_size_mb=1)
    await login(client, scenario.student.correo)

    response = await post_submission(
        client,
        str(scenario.deliverable["id"]),
        files=files,
        link_url=link_url,
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == expected_code

    detail = await client.get(f"/api/v1/deliverables/{scenario.deliverable['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "pending"
    assert detail.json()["version_count"] == 0


async def test_stored_file_metadata_preserves_mime_and_hash(
    client: AsyncClient,
) -> None:
    scenario = await setup_upload_scenario(client, formats=["pdf", "zip"])
    await login(client, scenario.student.correo)
    payload = PDF_BYTES + b"metadata"

    response = await post_submission(
        client,
        str(scenario.deliverable["id"]),
        files=[("files", ("informe.pdf", payload, "application/pdf"))],
    )

    assert response.status_code == 201, response.text
    uploaded_file = response.json()["files"][0]
    assert uploaded_file["original_name"] == "informe.pdf"
    assert uploaded_file["mime_type"] == "application/pdf"
    assert uploaded_file["size_bytes"] == len(payload)
    assert len(uploaded_file["sha256"]) == 64

    detail = await client.get(f"/api/v1/deliverables/{scenario.deliverable['id']}")
    assert detail.status_code == 200
    latest = detail.json()["latest_submission"]
    assert latest is not None
    assert latest["version"] == 1
