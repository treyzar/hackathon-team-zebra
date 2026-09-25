from pydantic import BaseModel


class StepProgress(BaseModel):
    # not_started | checking | failed | attempts_exhausted | partial | passed
    state: str
    # Best result, as a share of the step's current max_score.
    earned: float
    max_score: int
    # Who graded the best submission: "auto" (checks, tests) or "curator".
    graded_by: str | None = None
    best_submission_id: int | None = None
    # The best result was earned on a version of the step before a breaking
    # change; it still counts, and the step may be taken again.
    from_previous_version: bool = False
    # Counts towards the course percent: passed, or points with no attempts
    # left, or accepted by a curator (see progress/service.py).
    completed: bool = False


class StepProgressDetail(StepProgress):
    step_id: int
    module_id: int
    type: str
    # For the current version of the step.
    attempts_used: int
    max_attempts: int | None


class Totals(BaseModel):
    """Totals over a set of steps: a whole course or one module."""

    steps_total: int
    # Completed steps; of them, steps_passed reached the maximum.
    steps_completed: int
    steps_passed: int
    points_earned: float
    points_max: int
    # steps_completed / steps_total, in whole percents.
    percent: int


class ProgressSummary(Totals):
    # First open step to work on next; None when nothing is left to do.
    next_step_id: int | None


class ModuleProgress(Totals):
    module_id: int
    title: str


class CourseProgressOut(ProgressSummary):
    course_id: int
    modules: list[ModuleProgress]
    steps: list[StepProgressDetail]


class StudentProgressRow(BaseModel):
    student_id: int
    username: str
    progress: ProgressSummary


class Opportunity(BaseModel):
    """A step where the student can still earn points."""

    step_id: int
    module_id: int
    module_title: str
    # 1-based number of the step within its module, as the student sees it.
    position: int
    type: str
    # complete: not started or no points yet; improve: partial points.
    action: str
    # Points the step can still add (up to its maximum).
    can_gain: float


class RankTarget(BaseModel):
    place: int
    points: float
    # To overtake, earn MORE than this; equal points only share the place.
    # None when the student is already there.
    gap: float | None
    # Steps (ids from opportunities, in course order) that are enough to
    # overtake; reachable is False when all opportunities together are not.
    plan: list[int]
    reachable: bool


class MyRating(BaseModel):
    course_id: int
    group_size: int
    points: float
    place: int
    # How many other students have exactly the same points.
    tied_with: int
    # The nearest higher result; None when the student is first.
    next_place: RankTarget | None
    first_place: RankTarget
    opportunities: list[Opportunity]


class RatingRow(BaseModel):
    place: int
    student_id: int
    username: str
    points: float
    steps_completed: int
