from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from courses.models import Course, Step
from models import BaseDB, User


class Group(BaseDB):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    curator_id: Mapped[int | None] = mapped_column(
        ForeignKey(User.id, ondelete="SET NULL"), index=True
    )


class GroupStudent(BaseDB):
    # A student belongs to at most one group, hence user_id is the key.
    user_id: Mapped[int] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey(Group.id, ondelete="CASCADE"), index=True
    )


class Deadline(BaseDB):
    """A deadline a curator or admin set for one step, for one group.

    Only deadlines set by people are stored. Steps before it without their own
    deadline inherit it when shown (see groups/deadlines.py).
    """

    __table_args__ = (UniqueConstraint("group_id", "step_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey(Group.id, ondelete="CASCADE"))
    step_id: Mapped[int] = mapped_column(
        ForeignKey(Step.id, ondelete="CASCADE"), index=True
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    set_by: Mapped[int | None] = mapped_column(ForeignKey(User.id, ondelete="SET NULL"))


class GroupCourseDeadline(BaseDB):
    """An explicit course deadline for one group, set by its curator or an admin."""

    __table_args__ = (UniqueConstraint("group_id", "course_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey(Group.id, ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey(Course.id, ondelete="CASCADE"))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    set_by: Mapped[int | None] = mapped_column(ForeignKey(User.id, ondelete="SET NULL"))
