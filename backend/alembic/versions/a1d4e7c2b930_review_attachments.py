"""review attachments

Revision ID: a1d4e7c2b930
Revises: 9f3c2a1b7d4e
Create Date: 2026-11-17 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1d4e7c2b930"
down_revision: str | Sequence[str] | None = "d5f2a8c4e1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "archivo",
        "entrega_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.add_column(
        "archivo",
        sa.Column("revision_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_archivo_revision_id_revision",
        "archivo",
        "revision",
        ["revision_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_archivo_revision_id",
        "archivo",
        ["revision_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_archivo_un_propietario",
        "archivo",
        "num_nonnulls(entrega_id, revision_id) = 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_archivo_un_propietario",
        "archivo",
        type_="check",
    )
    op.drop_index("ix_archivo_revision_id", table_name="archivo")
    op.drop_constraint(
        "fk_archivo_revision_id_revision",
        "archivo",
        type_="foreignkey",
    )

    # Los archivos de revisión no caben en el esquema anterior.
    op.execute("DELETE FROM archivo WHERE revision_id IS NOT NULL")
    op.drop_column("archivo", "revision_id")
    op.alter_column(
        "archivo",
        "entrega_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
