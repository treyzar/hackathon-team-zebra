"""Falling behind schedule: a student's status in a course.

A step is overdue when its deadline (own or inherited, for the student's
group) has passed and the step is not completed. Steps waiting for a check
are not overdue: the student has done their part. A step with no points and
no attempts left stays overdue — it cannot be fixed, and the curator needs to
see it. Completing a step late clears it (the submission keeps its ``is_late``
mark). Deadlines never block submissions: they only feed this status.

Status: on_track — nothing overdue; slowed — overdue steps, none by more than
a week; falling_behind — at least one overdue by more than a week. The
overdue steps, most overdue first, are the reason the curator sees.
"""

import enum
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from courses.models import Course
from groups.deadlines import effective_deadlines
from progress.schemas import Lag, OverdueStep
from progress.service import CourseProgress, StepState, step_labels

GRACE = timedelta(days=7)


class LagStatus(enum.StrEnum):
    ON_TRACK = "on_track"
    SLOWED = "slowed"
    FALLING_BEHIND = "falling_behind"


async def group_lag(
    db: AsyncSession,
    course: Course,
    group_id: int | None,
    progress: dict[int, CourseProgress],
    now: datetime | None = None,
) -> dict[int, Lag]:
    """Lag of each student (by user id) of one group in the course."""
    now = now or datetime.now(UTC)
    deadlines = await effective_deadlines(db, group_id, course.id)
    any_progress = next(iter(progress.values()), None)
    steps = [r.step for r in any_progress.steps] if any_progress else []
    labels = await step_labels(db, course.id, steps)

    result = {}
    for user_id, p in progress.items():
        overdue = []
        for r in p.steps:
            eff = deadlines.get(r.step.id)
            if eff is None or eff.due_at >= now:
                continue
            if r.completed or r.state == StepState.CHECKING:
                continue
            overdue.append(
                OverdueStep(
                    step_id=r.step.id,
                    module_id=r.step.module_id,
                    module_title=labels[r.step.id].module_title,
                    position=labels[r.step.id].position,
                    type=r.step.type,
                    due_at=eff.due_at,
                    days_overdue=(now - eff.due_at).days,
                    state=r.state,
                )
            )
        overdue.sort(key=lambda o: o.due_at)
        if not overdue:
            status = LagStatus.ON_TRACK
        elif now - overdue[0].due_at > GRACE:
            status = LagStatus.FALLING_BEHIND
        else:
            status = LagStatus.SLOWED
        result[user_id] = Lag(status=status, overdue=overdue)
    return result
