from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app

TRUNCATE_TABLES = """
TRUNCATE TABLE
    revision,
    archivo,
    entrega,
    comentario,
    entregable,
    hito,
    participacion,
    plantilla,
    item_plantilla,
    notificacion,
    registro_auditoria,
    sesion,
    proyecto,
    usuario
RESTART IDENTITY CASCADE
"""


@pytest.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    """Deja la base de pruebas vacía antes de cada test."""
    async with SessionLocal() as db:
        await db.execute(text(TRUNCATE_TABLES))
        await db.commit()
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
