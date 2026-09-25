"""Curators review submissions of students from their groups; admins see all."""

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from access_docs import access_note
from auth import require_curator
from courses import service as svc
from courses.models import Course, Module, Step, StepRevision
from database import access_db
from groups.deadlines import is_late, submission_deadlines
from groups.service import students_of_curator
from models import Role, User
from submissions import service as sub_svc
from submissions.models import Submission, SubmissionStatus

review = APIRouter(prefix="/review", tags=["review"])


class ReviewListItem(BaseModel):
    id: int
    status: SubmissionStatus
    created_at: datetime
    auto_score: float | None
    score: float | None
    student_id: int
    student_username: str
    student_name: str
    student_surname: str
    student_patronymic: str
    step_id: int
    step_type: str
    max_score: int
    course_id: int
    task_title: str
    task_number: str
    course_title: str
    module_title: str
    # Deadline of the step for the student's group and whether the
    # submission came after it (a mark only).
    deadline_due_at: datetime | None
    is_late: bool
    # How long it has waited for a curator, counted from the moment it was
    # sent (for tests + review that includes the short judge run); null once
    # it is not waiting any more. Computed per request, not stored.
    waiting_seconds: int | None
    attempts_before: int


class CourseQueue(BaseModel):
    course_id: int
    course_title: str
    # Whole queue of the course, even when ``submissions`` is cut.
    total: int
    late: int
    oldest_at: datetime
    longest_waiting_seconds: int
    submissions: list[ReviewListItem]


class ReviewDetail(ReviewListItem):
    answer: dict[str, Any]
    result_details: dict[str, Any]
    is_outdated: bool
    review_comment: str | None
    reviewer_id: int | None
    reviewed_at: datetime | None
    # The revision the student answered, including the reference answer.
    content: dict[str, Any]
    answer_key: dict[str, Any]
    settings: dict[str, Any]


class Verdict(BaseModel):
    verdict: Literal["accepted", "rejected"]
    # Default: accepted -> score from tests (or max), rejected -> 0.
    score: float | None = Field(default=None, ge=0)
    comment: str | None = Field(default=None, max_length=10_000)


def _visible(user: User) -> Select:
    # Алиас для "предыдущих" сабмитов того же пользователя/шага
    prev = aliased(Submission)

    prev_attempts = (
        select(func.count(prev.id))
        .where(
            and_(
                prev.user_id == Submission.user_id,
                prev.step_id == Submission.step_id,
                prev.id < Submission.id,
            )
        )
        .correlate(Submission)
        .scalar_subquery()
        .label("attempts_before")
    )

    query = (
        select(
            Submission,
            User,
            Step,
            StepRevision,
            Module,
            Course,
            prev_attempts,
        )
        .join(User, User.id == Submission.user_id)
        .join(Step, Step.id == Submission.step_id)
        .join(StepRevision, StepRevision.id == Submission.step_revision_id)
        .join(Module, Module.id == Step.module_id)
        .join(Course, Course.id == Module.course_id)
    )
    if user.role != Role.ADMIN:
        query = query.where(Submission.user_id.in_(students_of_curator(user.id)))
    return query


def get_step_title(rev_content: dict) -> str | None:
    for node in rev_content.get("content", []):
        if node.get("type") == "heading" and node.get("attrs", {}).get("zebra_title"):
            return "".join(
                child.get("text", "")
                for child in node.get("content", [])
                if child.get("type") == "text"
            )
    return "заглушка"


def _item(row, due_at, cls=ReviewListItem, **extra):
    sub, student, step, rev, module, course, attempts_before = row
    return cls(
        deadline_due_at=due_at,
        is_late=is_late(sub, due_at),
        waiting_seconds=(
            int((svc.now() - sub.created_at).total_seconds())
            if sub.status == SubmissionStatus.PENDING_REVIEW
            else None
        ),
        attempts_before=attempts_before,
        id=sub.id,
        status=sub.status,
        created_at=sub.created_at,
        auto_score=sub.auto_score,
        score=sub.score,
        student_id=student.id,
        student_username=student.username,
        student_name=student.name,
        student_surname=student.surname,
        student_patronymic=student.patronymic,
        step_id=step.id,
        step_type=step.type,
        max_score=rev.max_score,
        course_id=course.id,
        task_title=get_step_title(rev.content),
        task_number=f"{module.position}.{step.position}",
        course_title=course.title,
        module_title=module.title,
        **extra,
    )


async def _get(db: AsyncSession, user: User, submission_id: int, lock=False):
    query = _visible(user).where(Submission.id == submission_id)
    if lock:
        query = query.with_for_update(of=Submission)
    row = (await db.execute(query)).one_or_none()
    if not row:
        # 404, not 403: do not reveal submissions of other groups.
        raise svc.not_found("Submission")
    return row


async def _detail(db: AsyncSession, row) -> ReviewDetail:
    sub, _, step, rev, _, _, _ = row
    parsed = svc.parse(step, rev)
    due = await submission_deadlines(db, [sub])
    return _item(
        row,
        due[sub.id],
        ReviewDetail,
        answer=sub.answer,
        result_details=sub.result_details,
        is_outdated=sub.is_outdated,
        review_comment=sub.review_comment,
        reviewer_id=sub.reviewer_id,
        reviewed_at=sub.reviewed_at,
        content=parsed.content.model_dump(mode="json"),
        answer_key=parsed.answer_key.model_dump(mode="json"),
        settings=parsed.settings.model_dump(mode="json"),
    )


@review.get("/submissions", response_model=list[ReviewListItem])
@access_note("Куратор видит только решения учеников своих групп, администратор — все.")
async def list_submissions(
    status: SubmissionStatus | None = SubmissionStatus.PENDING_REVIEW,
    course_id: int | None = None,
    student_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    """Oldest first, so the queue is worked in order."""
    query = _visible(user)
    if status is not None:
        query = query.where(Submission.status == status)
    if course_id is not None:
        query = query.where(Course.id == course_id)
    if student_id is not None:
        query = query.where(Submission.user_id == student_id)
    query = query.order_by(Submission.id).limit(limit).offset(offset)
    rows = (await db.execute(query)).all()
    due = await submission_deadlines(db, [row[0] for row in rows])
    return [_item(row, due[row[0].id]) for row in rows]


@review.get("/courses", response_model=list[CourseQueue])
@access_note("Куратор видит только решения учеников своих групп, администратор — все.")
async def queue_by_course(
    student_id: int | None = None,
    per_course: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    """Решения, ждущие ручной проверки, по курсам.

    Курсы — начиная с того, где работа ждёт дольше всех; внутри курса —
    от старых к новым. `total`, `late` и `longest_waiting_seconds` — по всей
    очереди курса, даже если `submissions` обрезан до `per_course`
    (остальное — через `GET /review/submissions?course_id=`).
    `waiting_seconds` у решения — сколько секунд оно ждёт с момента отправки."""
    query = _visible(user).where(Submission.status == SubmissionStatus.PENDING_REVIEW)
    if student_id is not None:
        query = query.where(Submission.user_id == student_id)
    # The whole queue is loaded: counts and "late" marks are computed, not
    # stored, and a pending-review queue stays small.
    rows = (await db.execute(query.order_by(Submission.id))).all()
    due = await submission_deadlines(db, [row[0] for row in rows])

    # Rows go oldest first, so courses are met in order of their oldest work.
    by_course: dict[int, list[ReviewListItem]] = {}
    for row in rows:
        by_course.setdefault(row[5].id, []).append(_item(row, due[row[0].id]))
    return [
        CourseQueue(
            course_id=items[0].course_id,
            course_title=items[0].course_title,
            total=len(items),
            late=sum(i.is_late for i in items),
            oldest_at=min(i.created_at for i in items),
            longest_waiting_seconds=max(i.waiting_seconds or 0 for i in items),
            submissions=items[:per_course],
        )
        for items in by_course.values()
    ]


@review.get("/submissions/{submission_id}", response_model=ReviewDetail)
@access_note("Куратор видит только решения учеников своих групп, администратор — все.")
async def get_submission(
    submission_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    return await _detail(db, await _get(db, user, submission_id))


@review.post("/submissions/{submission_id}", response_model=ReviewDetail)
@access_note(
    "Куратор видит только решения учеников своих групп, администратор — все. "
    "Вердикт выносится только для решения в статусе `pending_review`."
)
async def review_submission(
    submission_id: int,
    data: Verdict,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    row = await _get(db, user, submission_id, lock=True)
    sub, rev = row[0], row[3]
    await sub_svc.apply_review(
        db,
        sub,
        user,
        data.verdict == "accepted",
        data.score,
        data.comment,
        rev.max_score,
    )
    await db.flush()
    return await _detail(db, row)
