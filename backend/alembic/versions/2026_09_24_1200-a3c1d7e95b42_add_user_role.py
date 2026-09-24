"""add user role

Revision ID: a3c1d7e95b42
Revises: fea10e892ff0
Create Date: 2026-09-24 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c1d7e95b42"
down_revision: str | Sequence[str] | None = "fea10e892ff0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum(
                "student", "curator", "admin", name="role", native_enum=False, length=16
            ),
            server_default="student",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "role")
