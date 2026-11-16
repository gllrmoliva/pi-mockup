from enum import Enum as PyEnum

from sqlalchemy import Enum as SAEnum


def _enum_values(enum_cls: type[PyEnum]) -> list[str]:
    return [member.value for member in enum_cls]


def pg_enum(enum_cls: type[PyEnum], name: str) -> SAEnum:
    """Crea un enum nativo de PostgreSQL usando los valores del enum de Python."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=_enum_values,
    )
