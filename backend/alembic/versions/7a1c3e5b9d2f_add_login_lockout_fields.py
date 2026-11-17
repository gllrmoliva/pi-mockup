"""add login lockout fields

Revision ID: 7a1c3e5b9d2f
Revises: 9f3c2a1b7d4e
Create Date: 2026-11-16 22:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a1c3e5b9d2f"
down_revision: str | Sequence[str] | None = "9f3c2a1b7d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column(
            "intentos_fallidos",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "usuario",
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuario", "bloqueado_hasta")
    op.drop_column("usuario", "intentos_fallidos")
