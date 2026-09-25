import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from courses.models import Step
from groups.models import Group
from models import BaseDB, User


class QuestionVisibility(enum.StrEnum):
    # The author, the curator of the author's group and admins.
    PRIVATE = "private"
    # Also the students of ``Question.group_id``.
    GROUP = "group"
    # Also every student who may open the step.
    COURSE = "course"


class Question(BaseDB):
    """A student's question about a step and the single answer to it."""

    id: Mapped[int] = mapped_column(primary_key=True)
    step_id: Mapped[int] = mapped_column(
        ForeignKey(Step.id, ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)

    answer: Mapped[str | None] = mapped_column(Text)
    answered_by: Mapped[int | None] = mapped_column(
        ForeignKey(User.id, ondelete="SET NULL")
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    visibility: Mapped[QuestionVisibility] = mapped_column(
        Enum(
            QuestionVisibility,
            native_enum=False,
            length=16,
            values_callable=lambda e: [v.value for v in e],
        ),
        default=QuestionVisibility.PRIVATE,
    )
    # Stored, not derived from the author's membership: the curator opened the
    # question to this particular group, and it stays there if the author
    # moves to another group later.
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey(Group.id, ondelete="SET NULL")
    )
