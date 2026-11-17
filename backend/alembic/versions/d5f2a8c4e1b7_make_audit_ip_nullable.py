"""make audit ip nullable

Revision ID: d5f2a8c4e1b7
Revises: 7a1c3e5b9d2f
Create Date: 2026-11-17 02:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5f2a8c4e1b7"
down_revision: str | Sequence[str] | None = "7a1c3e5b9d2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "registro_auditoria",
        "ip",
        existing_type=sa.String(length=45),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE registro_auditoria SET ip = 'unknown' WHERE ip IS NULL")
    op.alter_column(
        "registro_auditoria",
        "ip",
        existing_type=sa.String(length=45),
        nullable=False,
    )
