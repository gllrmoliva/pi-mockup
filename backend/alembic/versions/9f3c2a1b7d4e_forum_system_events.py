"""forum system events

Revision ID: 9f3c2a1b7d4e
Revises: 268f9b6af92d
Create Date: 2026-11-16 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9f3c2a1b7d4e"
down_revision: str | Sequence[str] | None = "268f9b6af92d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    forum_message_type = postgresql.ENUM(
        "usuario",
        "sistema",
        name="forum_message_type",
    )
    forum_message_type.create(bind, checkfirst=True)

    op.add_column(
        "comentario",
        sa.Column(
            "tipo",
            postgresql.ENUM(
                "usuario",
                "sistema",
                name="forum_message_type",
                create_type=False,
            ),
            server_default=sa.text("'usuario'"),
            nullable=False,
        ),
    )
    op.alter_column(
        "comentario",
        "autor_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_comentario_autor_por_tipo",
        "comentario",
        (
            "(tipo = 'usuario' AND autor_id IS NOT NULL) OR "
            "(tipo = 'sistema' AND autor_id IS NULL)"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_comentario_autor_por_tipo",
        "comentario",
        type_="check",
    )

    # Los eventos automáticos no tienen autor y no caben en el esquema anterior.
    op.execute("DELETE FROM comentario WHERE tipo = 'sistema'")

    op.alter_column(
        "comentario",
        "autor_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_column("comentario", "tipo")

    postgresql.ENUM(name="forum_message_type").drop(
        bind=op.get_bind(),
        checkfirst=True,
    )
