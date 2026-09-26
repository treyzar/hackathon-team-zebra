import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models import BaseDB, User


class StepAccess(enum.StrEnum):
    ALL = "all"  # every step is open from the start
    # A step opens once the previous one is passed: some score, attempts used
    # up, or a submission sent to a curator (see courses/access.py).
    SEQUENTIAL = "sequential"


class Course(BaseDB):
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    # TipTap/ProseMirror JSON document.
    description: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    step_access: Mapped[StepAccess] = mapped_column(
        Enum(
            StepAccess,
            native_enum=False,
            length=16,
            values_callable=lambda e: [v.value for v in e],
        ),
        default=StepAccess.ALL,
        server_default=StepAccess.ALL.value,
    )
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Module(BaseDB):
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey(Course.id, ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Step(BaseDB):
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey(Module.id, ondelete="CASCADE"), index=True
    )
    # Fixed for the lifetime of the step; a different type is a new step.
    type: Mapped[str] = mapped_column(String(32))
    position: Mapped[int] = mapped_column(Integer)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    current_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("steprevisions.id", use_alter=True, name="fk_steps_current_revision")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StepRevision(BaseDB):
    """Immutable snapshot of a step; every save creates a new one."""

    __table_args__ = (UniqueConstraint("step_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    step_id: Mapped[int] = mapped_column(
        ForeignKey(Step.id, ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    answer_key: Mapped[dict[str, Any]] = mapped_column(JSONB)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB)
    schema_version: Mapped[int] = mapped_column(Integer)
    max_score: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey(User.id, ondelete="SET NULL")
    )
    comment: Mapped[str | None] = mapped_column(Text)
    # Correct answer changed: earlier submissions are marked outdated.
    is_breaking: Mapped[bool] = mapped_column(Boolean, default=False)


class Enrollment(BaseDB):
    """A student enrolled in a course: students see only their courses."""

    course_id: Mapped[int] = mapped_column(
        ForeignKey(Course.id, ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), primary_key=True, index=True
    )
    enrolled_by: Mapped[int | None] = mapped_column(
        ForeignKey(User.id, ondelete="SET NULL")
    )
