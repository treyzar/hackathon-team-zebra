"""Add an optional course deadline.

Revision ID: 8158a2d431cb
Revises: 907e6a146fd3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8158a2d431cb"
down_revision: str | Sequence[str] | None = "907e6a146fd3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("deadline_at", sa.DateTime(timezone=True)))
    op.create_table(
        "groupcoursedeadlines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("set_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("group_id", "course_id"),
    )


def downgrade() -> None:
    op.drop_table("groupcoursedeadlines")
    op.drop_column("courses", "deadline_at")
