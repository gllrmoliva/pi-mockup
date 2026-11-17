import pytest
from sqlalchemy import text

from app.db.base import Base
from app.db.models import (
    Archivo,
    Comentario,
    Entrega,
    Entregable,
    Hito,
    ItemPlantilla,
    Notificacion,
    Participacion,
    Plantilla,
    Proyecto,
    RegistroAuditoria,
    Revision,
    Sesion,
    Usuario,
)
from app.db.session import SessionLocal

pytestmark = pytest.mark.nfr

FORBIDDEN_COLUMNS = {
    "rut",
    "run",
    "nota",
    "notas",
    "calificacion",
    "calificaciones",
    "grade",
    "grades",
}
FORBIDDEN_TABLES = {
    "nota",
    "notas",
    "calificacion",
    "calificaciones",
    "grade",
    "grades",
}
EXPECTED_TABLES = {
    Archivo.__tablename__,
    Comentario.__tablename__,
    Entregable.__tablename__,
    Entrega.__tablename__,
    Hito.__tablename__,
    ItemPlantilla.__tablename__,
    Notificacion.__tablename__,
    Participacion.__tablename__,
    Plantilla.__tablename__,
    Proyecto.__tablename__,
    RegistroAuditoria.__tablename__,
    Revision.__tablename__,
    Sesion.__tablename__,
    Usuario.__tablename__,
}


def test_metadata_declares_all_models() -> None:
    assert set(Base.metadata.tables) >= EXPECTED_TABLES


def test_metadata_has_no_rut_or_grade_columns() -> None:
    found = [
        (table.name, column.name)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if column.name.lower() in FORBIDDEN_COLUMNS
    ]

    assert found == []


async def test_database_schema_has_no_rut_or_grade_columns() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT table_name, column_name "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public'"
            )
        )
        rows = result.all()

    found_columns = [
        (str(table_name), str(column_name))
        for table_name, column_name in rows
        if str(column_name).lower() in FORBIDDEN_COLUMNS
    ]
    found_tables = {
        str(table_name)
        for table_name, _ in rows
        if str(table_name).lower() in FORBIDDEN_TABLES
    }

    assert found_columns == []
    assert found_tables == set()
