"""Course progress of students.

Progress answers "how far through the course am I, and how well": the number
of passed steps and the points earned, with a breakdown per step. It is
computed from submissions on request (one query for any number of students),
so nothing has to be recalculated when a course or a result changes.

Rules (also described in README):

- A step's result is its best submission. Automatic and curator grading count
  the same way.
- A step is passed when its maximum is reached; a step without points
  (theory) when it was completed.
- A step is completed (counts towards the course percent) when it cannot be
  improved any more or a curator accepted it: passed, or some points with no
  attempts left (9 of 10 is done), or accepted by a curator with any score.
  No points and no attempts left is not completed.
- Only visible steps count: a new step appears as not started and raises the
  totals; hidden or deleted steps drop out, their submissions stay in history;
  reordering changes nothing.
- A breaking change of a step keeps the earlier result (it is not lost), the
  student just gets fresh attempts for the new version. If the change also
  changed max_score, the earlier score keeps its share of the maximum:
  2 of 2 before becomes 4 of 4 after.
"""

import enum
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from courses.access import locked_steps
from courses.models import Course, StepRevision
from courses.service import OrderedStep, visible_steps_in_order
from models import User
from progress.schemas import ProgressSummary, StepProgress, StepProgressDetail, Totals
from submissions.models import Submission, SubmissionStatus


class StepState(enum.StrEnum):
    NOT_STARTED = "not_started"
    CHECKING = "checking"  # queued, running tests or waiting for a curator
    FAILED = "failed"  # tried, no points yet, may try again
    ATTEMPTS_EXHAUSTED = "attempts_exhausted"  # no points and no tries left
    PARTIAL = "partial"
    PASSED = "passed"


_BY_CURATOR = {SubmissionStatus.ACCEPTED, SubmissionStatus.REJECTED}


@dataclass
class StepResult:
    step: OrderedStep
    state: StepState = StepState.NOT_STARTED
    earned: float = 0.0
    graded_by: str | None = None
    best_submission_id: int | None = None
    from_previous_version: bool = False
    attempts_used: int = 0
    completed: bool = False

    @property
    def max_attempts(self) -> int | None:
        return self.step.settings.get("max_attempts")

    @property
    def attempts_left(self) -> bool:
        return self.max_attempts is None or self.attempts_used < self.max_attempts

    def as_schema(self) -> StepProgress:
        return StepProgress(
            state=self.state,
            earned=self.earned,
            max_score=self.step.max_score,
            graded_by=self.graded_by,
            best_submission_id=self.best_submission_id,
            from_previous_version=self.from_previous_version,
            completed=self.completed,
        )

    def as_detail(self) -> StepProgressDetail:
        return StepProgressDetail(
            **self.as_schema().model_dump(),
            step_id=self.step.id,
            module_id=self.step.module_id,
            type=self.step.type,
            attempts_used=self.attempts_used,
            max_attempts=self.max_attempts,
        )


@dataclass
class CourseProgress:
    steps: list[StepResult]
    next_step_id: int | None = None
    by_step: dict[int, StepResult] = field(init=False)

    def __post_init__(self):
        self.by_step = {r.step.id: r for r in self.steps}

    def summary(self) -> ProgressSummary:
        return ProgressSummary(
            **_totals(self.steps).model_dump(), next_step_id=self.next_step_id
        )

    def module_totals(self, module_id: int) -> Totals:
        """The same totals over the module's steps; the course totals are the
        sum over its modules."""
        return _totals([r for r in self.steps if r.step.module_id == module_id])


def _totals(results: list[StepResult]) -> Totals:
    completed = sum(r.completed for r in results)
    total = len(results)
    return Totals(
        steps_total=total,
        steps_completed=completed,
        steps_passed=sum(r.state == StepState.PASSED for r in results),
        points_earned=round(sum(r.earned for r in results), 2),
        points_max=sum(r.step.max_score for r in results),
        percent=round(100 * completed / total) if total else 0,
    )


def _share(score: float, graded_max: int, current_max: int) -> float:
    """Score of a submission in terms of the step's current maximum."""
    if graded_max == current_max:
        return score
    return score / graded_max * current_max if graded_max else 0.0


def _step_result(step: OrderedStep, rows: list) -> StepResult:
    result = StepResult(step=step)
    best = None
    tried = solved = checking = accepted = False
    for sub_id, status, score, is_outdated, graded_max in rows:
        if status == SubmissionStatus.ERROR:  # judge failure, not an attempt
            continue
        tried = True
        solved |= status.solved
        accepted |= status == SubmissionStatus.ACCEPTED
        if not is_outdated:
            result.attempts_used += 1
            checking |= status.in_progress
        if score is None:
            continue
        earned = round(_share(score, graded_max, step.max_score), 2)
        if best is None or earned > best[0]:
            best = (earned, sub_id, status, is_outdated)

    if best is not None:
        result.earned, result.best_submission_id, status, outdated = best
        result.graded_by = "curator" if status in _BY_CURATOR else "auto"
        result.from_previous_version = outdated

    if (step.max_score > 0 and result.earned >= step.max_score) or (
        step.max_score == 0 and solved
    ):
        result.state = StepState.PASSED
    elif checking:
        result.state = StepState.CHECKING
    elif result.earned > 0:
        result.state = StepState.PARTIAL
    elif tried and not result.attempts_left:
        result.state = StepState.ATTEMPTS_EXHAUSTED
    elif tried:
        result.state = StepState.FAILED

    result.completed = (
        result.state == StepState.PASSED
        or (result.earned > 0 and not result.attempts_left)
        or accepted
    )
    return result


def _next_step(results: list[StepResult], locked: set[int]) -> int | None:
    """What to do next: the first open step not tried or not solved yet;
    otherwise one with partial points that can still be improved."""
    open_steps = [r for r in results if r.step.id not in locked]
    for r in open_steps:
        if r.state in (StepState.NOT_STARTED, StepState.FAILED):
            return r.step.id
    for r in open_steps:
        if r.state == StepState.PARTIAL and r.attempts_left:
            return r.step.id
    return None


async def course_progress(
    db: AsyncSession, course: Course, users: list[User]
) -> dict[int, CourseProgress]:
    """Progress of each user in the course, keyed by user id."""
    order = await visible_steps_in_order(db, course.id)
    rows = await db.execute(
        select(
            Submission.user_id,
            Submission.step_id,
            Submission.id,
            Submission.status,
            Submission.score,
            Submission.is_outdated,
            # max_score of the revision the submission was graded against
            StepRevision.max_score,
        )
        .join(StepRevision, StepRevision.id == Submission.step_revision_id)
        .where(
            Submission.user_id.in_([u.id for u in users]),
            Submission.step_id.in_([s.id for s in order]),
        )
    )
    grouped: dict[tuple[int, int], list] = defaultdict(list)
    for user_id, step_id, *rest in rows:
        grouped[(user_id, step_id)].append(rest)

    progress = {}
    for user in users:
        results = [_step_result(s, grouped.get((user.id, s.id), [])) for s in order]
        locked = await locked_steps(db, user, course)
        progress[user.id] = CourseProgress(results, _next_step(results, locked))
    return progress
