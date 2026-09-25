"""Which steps of a course a student may open (the course's step_access)."""

from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from courses.models import Course, Enrollment, Module, Step, StepAccess
from courses.service import get_step, visible_steps_in_order
from models import Role, User
from submissions.models import Submission, SubmissionStatus

# Statuses meaning "sent to a curator", whatever the verdict.
_REVIEWED = {
    SubmissionStatus.PENDING_REVIEW,
    SubmissionStatus.ACCEPTED,
    SubmissionStatus.REJECTED,
}


async def locked_steps(db: AsyncSession, user: User, course: Course) -> set[int]:
    """Ids of the course's visible steps the user may not open yet.

    In a sequential course a step opens when the previous visible step (in
    module, then step order) is passed: it got some score, was solved (theory
    has no score), its attempts are used up, or it was sent to a curator.
    A step the student already submitted to stays open, so reordering steps or
    changing an earlier one never takes away access to their own work.
    Outdated submissions count too: once opened, a step stays open.
    Admins and curators see everything.
    """
    if course.step_access == StepAccess.ALL or user.role != Role.STUDENT:
        return set()

    # max_attempts is a CommonSettings field, present in every step type.
    order = [
        (s.id, s.settings.get("max_attempts"))
        for s in await visible_steps_in_order(db, course.id)
    ]

    subs = await db.execute(
        select(Submission.step_id, Submission.status, Submission.score).where(
            Submission.user_id == user.id,
            Submission.step_id.in_([step_id for step_id, _ in order]),
        )
    )
    by_step: dict[int, list[tuple[SubmissionStatus, float | None]]] = defaultdict(list)
    for step_id, st, score in subs:
        by_step[step_id].append((st, score))

    def passed(step_id: int, max_attempts: int | None) -> bool:
        history = by_step.get(step_id, [])
        attempts = sum(1 for st, _ in history if st != SubmissionStatus.ERROR)
        return (
            any(score is not None and score > 0 for _, score in history)
            or any(st.solved or st in _REVIEWED for st, _ in history)
            or (max_attempts is not None and attempts >= max_attempts)
        )

    locked = set()
    for i, (step_id, _) in enumerate(order):
        if i == 0 or step_id in by_step:
            continue
        prev_id, prev_max_attempts = order[i - 1]
        if not passed(prev_id, prev_max_attempts):
            locked.add(step_id)
    return locked


async def ensure_unlocked(
    db: AsyncSession, user: User, step: Step, module: Module
) -> None:
    course = await db.get(Course, module.course_id)
    if step.id in await locked_steps(db, user, course):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "The step is locked until the previous step is passed",
        )


def enrolled_course_ids(user_id: int) -> Select[tuple[int]]:
    return select(Enrollment.course_id).where(Enrollment.user_id == user_id)


async def ensure_enrolled(db: AsyncSession, user: User, course_id: int) -> None:
    """Students see only the courses they are enrolled in; for others the
    course does not exist (404). Admins and curators see every course."""
    if user.role != Role.STUDENT:
        return
    if await db.get(Enrollment, (course_id, user.id)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")


async def open_step(db: AsyncSession, user: User, step_id: int):
    """A visible step the user may open: 404 if hidden or not enrolled,
    403 if still locked."""
    step, rev, module = await get_step(db, step_id, for_student=True)
    await ensure_enrolled(db, user, module.course_id)
    await ensure_unlocked(db, user, step, module)
    return step, rev, module
