"""Course analytics for one group: modules, students, step results.

Built on course progress (which step is completed, a step's state) and the
lag rule, so the numbers agree with what students and curators see
elsewhere. What only analytics needs is counted here from the submissions:

- An attempt is a submission, except judge failures (status ``error``).
  Attempts made before a breaking change of the step count too: analytics
  describes the work done, not what is left to do.
- A task is a step with points (theory is not a task).
- First attempt success: the first attempt reached its maximum. The share is
  taken over (student, task) pairs whose first attempt is already graded, so
  work waiting for a check does not lower it.
- A return is a submission a curator rejected. It is unresolved while it is
  the student's last attempt at the step.
- A module is passed when all its steps are completed, not started when the
  student has no attempts at any of its steps, in progress otherwise.
"""

import enum
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from courses.models import Course, Module, Step, StepRevision
from courses.service import get_step_title, live_modules, visible_steps_in_order
from models import User
from progress.lag import group_lag
from progress.schemas import (
    CourseAnalytics,
    ModuleAnalytics,
    ModuleStats,
    StepCell,
    StepColumn,
    StudentAnalytics,
    StudentInfo,
    StudentModule,
    StudentSteps,
)
from progress.service import CourseProgress, StepResult, course_progress
from submissions.models import Submission, SubmissionStatus


class ModuleState(enum.StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"


@dataclass
class _Work:
    """A student's attempts at one step, oldest first."""

    attempts: int = 0
    # None: the first attempt is not graded yet (or there is none).
    first_solved: bool | None = None
    returns: int = 0
    unresolved_return: bool = False
    last_at: datetime | None = None


async def _work(
    db: AsyncSession, students: list[User], step_ids: list[int]
) -> dict[tuple[int, int], _Work]:
    rows = await db.execute(
        select(
            Submission.user_id,
            Submission.step_id,
            Submission.status,
            Submission.score,
            Submission.created_at,
            # max_score of the revision the submission was graded against
            StepRevision.max_score,
        )
        .join(StepRevision, StepRevision.id == Submission.step_revision_id)
        .where(
            Submission.user_id.in_([s.id for s in students]),
            Submission.step_id.in_(step_ids),
            Submission.status != SubmissionStatus.ERROR,
        )
        .order_by(Submission.id)
    )
    work: dict[tuple[int, int], _Work] = defaultdict(_Work)
    for user_id, step_id, status, score, created_at, graded_max in rows:
        w = work[(user_id, step_id)]
        if w.attempts == 0 and score is not None:
            w.first_solved = graded_max > 0 and score >= graded_max
        w.attempts += 1
        w.returns += status == SubmissionStatus.REJECTED
        w.unresolved_return = status == SubmissionStatus.REJECTED
        w.last_at = created_at
    return dict(work)


def _module_state(results: list[StepResult], work, user_id: int) -> ModuleState:
    if results and all(r.completed for r in results):
        return ModuleState.PASSED
    if any(work.get((user_id, r.step.id)) for r in results):
        return ModuleState.IN_PROGRESS
    return ModuleState.NOT_STARTED


def _module_stats(module: Module, students: list[User], progress, work) -> ModuleStats:
    states = defaultdict(int)
    first_graded = first_solved = attempted = attempts = returns = 0
    for s in students:
        results = _module_results(progress[s.id], module.id)
        states[_module_state(results, work, s.id)] += 1
        for r in results:
            w = work.get((s.id, r.step.id))
            if w is None or r.step.max_score == 0:
                continue
            attempted += 1
            attempts += w.attempts
            returns += w.returns
            if w.first_solved is not None:
                first_graded += 1
                first_solved += w.first_solved
    return ModuleStats(
        module_id=module.id,
        title=module.title,
        students_passed=states[ModuleState.PASSED],
        students_in_progress=states[ModuleState.IN_PROGRESS],
        students_not_started=states[ModuleState.NOT_STARTED],
        first_attempt_percent=(
            round(100 * first_solved / first_graded) if first_graded else None
        ),
        avg_attempts=round(attempts / attempted, 2) if attempted else None,
        returns=returns,
    )


def _module_results(p: CourseProgress, module_id: int) -> list[StepResult]:
    return [r for r in p.steps if r.step.module_id == module_id]


def _student_info(s: User) -> StudentInfo:
    return StudentInfo(
        student_id=s.id,
        username=s.username,
        name=s.name,
        surname=s.surname,
        patronymic=s.patronymic,
    )


async def _collect(db: AsyncSession, course: Course, students: list[User]):
    progress = await course_progress(db, course, students)
    step_ids = [s.id for s in await visible_steps_in_order(db, course.id)]
    return progress, await _work(db, students, step_ids)


async def course_analytics(
    db: AsyncSession, course: Course, group_id: int, students: list[User]
) -> CourseAnalytics:
    modules = await live_modules(db, course.id)
    progress, work = await _collect(db, course, students)
    lag = await group_lag(db, course, group_id, progress)

    rows = []
    for s in students:
        student_modules = []
        for m in modules:
            results = _module_results(progress[s.id], m.id)
            tasks = [r for r in results if r.step.max_score > 0]
            student_modules.append(
                StudentModule(
                    module_id=m.id,
                    state=_module_state(results, work, s.id),
                    steps_total=len(results),
                    steps_completed=sum(r.completed for r in results),
                    has_submissions=any(work.get((s.id, r.step.id)) for r in tasks),
                    has_unresolved_return=any(
                        work[(s.id, r.step.id)].unresolved_return
                        for r in results
                        if (s.id, r.step.id) in work
                    ),
                )
            )
        last = [w.last_at for (uid, _), w in work.items() if uid == s.id]
        rows.append(
            StudentAnalytics(
                **_student_info(s).model_dump(),
                lag=lag[s.id],
                last_submission_at=max(last) if last else None,
                modules=student_modules,
            )
        )
    return CourseAnalytics(
        course_id=course.id,
        group_id=group_id,
        students_total=len(students),
        modules=[_module_stats(m, students, progress, work) for m in modules],
        students=rows,
    )


async def module_analytics(
    db: AsyncSession, course: Course, module: Module, students: list[User]
) -> ModuleAnalytics:
    progress, work = await _collect(db, course, students)
    steps = [
        s
        for s in await visible_steps_in_order(db, course.id)
        if s.module_id == module.id
    ]
    contents = dict(
        (
            await db.execute(
                select(Step.id, StepRevision.content)
                .join(StepRevision, StepRevision.id == Step.current_revision_id)
                .where(Step.id.in_([s.id for s in steps]))
            )
        ).all()
    )
    columns = [
        StepColumn(
            step_id=s.id,
            position=i,
            type=s.type,
            title=get_step_title(contents.get(s.id) or {}),
            max_score=s.max_score,
        )
        for i, s in enumerate(steps, start=1)
    ]
    rows = []
    for student in students:
        cells = []
        for r in _module_results(progress[student.id], module.id):
            w = work.get((student.id, r.step.id), _Work())
            cells.append(
                StepCell(
                    step_id=r.step.id,
                    state=r.state,
                    earned=r.earned,
                    max_score=r.step.max_score,
                    completed=r.completed,
                    attempts=w.attempts,
                    # Theory has nothing to solve.
                    first_attempt_solved=(
                        w.first_solved if r.step.max_score > 0 else None
                    ),
                    has_unresolved_return=w.unresolved_return,
                    last_submission_at=w.last_at,
                )
            )
        rows.append(StudentSteps(**_student_info(student).model_dump(), steps=cells))
    return ModuleAnalytics(
        course_id=course.id,
        module=_module_stats(module, students, progress, work),
        steps=columns,
        students=rows,
    )
