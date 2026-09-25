import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models import BaseDB, User


class NotificationType(enum.StrEnum):
    # payload: {step_id, course_id, deadline: datetime, hours_left: int}
    DEADLINE_APPROACHING = "deadline_approaching"
    # payload: {step_id, course_id, deadline: datetime}
    DEADLINE_PASSED = "deadline_passed"
    # payload: {step_id, course_id, deadline: datetime, previous: datetime | null}
    DEADLINE_CHANGED = "deadline_changed"

    # payload: {submission_id, step_id, course_id, verdict, score}
    SUBMISSION_REVIEWED = "submission_reviewed"
    # payload: {submission_id, step_id, student_id, student_username}
    SUBMISSION_PENDING_REVIEW = "submission_pending_review"
    # payload: {pending: int}
    SUBMISSION_QUEUE_REMINDER = "submission_queue_reminder"

    # payload: {question_id, step_id, course_id, student_id}
    QUESTION_ASKED = "question_asked"
    # payload: {question_id, step_id, course_id}
    QUESTION_ANSWERED = "question_answered"

    # payload: {step_id, course_id, score, max_score}
    STEP_SOLVED = "step_solved"
    # payload: {step_id, course_id, title}
    STEP_UNLOCKED = "step_unlocked"
    # payload: {step_id, course_id, outdated: int}
    STEP_BREAKING_CHANGE = "step_breaking_change"

    # payload: {course_id, course_title}
    COURSE_COMPLETED = "course_completed"
    COURSE_PUBLISHED = "course_published"
    COURSE_ATTENTION_NEEDED = "course_attention_needed"

    # payload: {group_id, group_name}
    ADDED_TO_GROUP = "added_to_group"
    MOVED_TO_GROUP = "moved_to_group"
    ASSIGNED_GROUP = "assigned_group"

    HELLO = "hello"
    ROLE_CHANGED = "role_changed"


class Severity(enum.StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


def _enum(e: type[enum.Enum], length: int) -> Enum:
    return Enum(
        e,
        native_enum=False,
        length=length,
        values_callable=lambda x: [v.value for v in x],
    )


class Notification(BaseDB):
    __table_args__ = (
        Index(
            "ix_notifications_user_unread",
            "user_id",
            postgresql_where=text("read_at IS NULL"),
        ),
        UniqueConstraint("user_id", "dedup_key", name="uq_notifications_user_dedup"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), index=True
    )
    type: Mapped[NotificationType] = mapped_column(_enum(NotificationType, 32))
    severity: Mapped[Severity] = mapped_column(
        _enum(Severity, 16), default=Severity.INFO, server_default=Severity.INFO.value
    )

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dedup_key: Mapped[str | None] = mapped_column(String(255))
