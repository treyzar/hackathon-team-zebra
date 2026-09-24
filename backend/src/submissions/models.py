import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from courses.models import Step, StepRevision
from models import BaseDB, User


class SubmissionStatus(enum.StrEnum):
    QUEUED = "queued"  # waiting for the judge worker
    RUNNING = "running"  # judge worker is running tests
    PENDING_REVIEW = "pending_review"  # waiting for the curator
    CORRECT = "correct"  # auto: full score
    PARTIAL = "partial"  # auto: some score
    WRONG = "wrong"  # auto: zero score
    ACCEPTED = "accepted"  # curator verdict
    REJECTED = "rejected"  # curator verdict
    ERROR = "error"  # judge kept failing; does not count as an attempt

    @property
    def in_progress(self) -> bool:
        return self in IN_PROGRESS

    @property
    def solved(self) -> bool:
        return self in (SubmissionStatus.CORRECT, SubmissionStatus.ACCEPTED)

    @property
    def failed(self) -> bool:
        return self in (
            SubmissionStatus.WRONG,
            SubmissionStatus.PARTIAL,
            SubmissionStatus.REJECTED,
        )


IN_PROGRESS = frozenset(
    {
        SubmissionStatus.QUEUED,
        SubmissionStatus.RUNNING,
        SubmissionStatus.PENDING_REVIEW,
    }
)


class Submission(BaseDB):
    __table_args__ = (
        Index("ix_submissions_user_step", "user_id", "step_id"),
        # The judge worker polls for queued submissions.
        Index("ix_submissions_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"))
    step_id: Mapped[int] = mapped_column(ForeignKey(Step.id, ondelete="CASCADE"))
    step_revision_id: Mapped[int] = mapped_column(
        ForeignKey(StepRevision.id, ondelete="CASCADE")
    )
    answer: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(
            SubmissionStatus,
            native_enum=False,
            length=16,
            values_callable=lambda e: [s.value for s in e],
        )
    )
    # Final score; None until grading is finished.
    score: Mapped[float | None] = mapped_column(Float)
    # Score from tests, the curator's starting point in tests_and_review.
    auto_score: Mapped[float | None] = mapped_column(Float)
    result_details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Set when the step got a breaking revision after this submission.
    is_outdated: Mapped[bool] = mapped_column(Boolean, default=False)

    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey(User.id, ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[str | None] = mapped_column(Text)

    judge_attempts: Mapped[int] = mapped_column(Integer, default=0)
    judge_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    judge_error: Mapped[str | None] = mapped_column(String(1000))
