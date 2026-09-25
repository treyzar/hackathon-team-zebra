from datetime import datetime

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


class OverdueStep(BaseModel):
    """A step whose deadline has passed and that is not completed yet."""

    step_id: int
    module_id: int
    module_title: str
    position: int
    type: str
    due_at: datetime
    days_overdue: int
    # Why it is stuck: not_started, failed (no points yet),
    # attempts_exhausted (no points and no tries left) or partial.
    state: str


class Lag(BaseModel):
    # on_track: nothing overdue; slowed: overdue, none by more than a week;
    # falling_behind: something is overdue by more than a week.
    status: str
    # The reason: overdue steps, the most overdue first.
    overdue: list[OverdueStep]


class CourseProgressOut(ProgressSummary):
    course_id: int
    lag: Lag
    modules: list[ModuleProgress]
    steps: list[StepProgressDetail]


class StudentProgressRow(BaseModel):
    student_id: int
    username: str
    progress: ProgressSummary
    lag: Lag


class StudentLagRow(BaseModel):
    student_id: int
    username: str
    lag: Lag


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


# --- analytics of a course for one group -----------------------------------


class ModuleStats(BaseModel):
    module_id: int
    title: str
    # Students of the group: all steps completed / some attempts / none.
    students_passed: int
    students_in_progress: int
    students_not_started: int
    # Of the (student, task) pairs whose first attempt is graded, how many
    # reached the maximum on it, in whole percents; null if there are none.
    first_attempt_percent: int | None
    # Attempts per (student, task) pair with at least one attempt.
    avg_attempts: float | None
    # Submissions rejected by a curator.
    returns: int


class StudentInfo(BaseModel):
    student_id: int
    username: str
    name: str
    surname: str
    patronymic: str


class StudentModule(BaseModel):
    module_id: int
    # passed | in_progress | not_started
    state: str
    steps_total: int
    steps_completed: int
    # Any attempt at a task (a step with points) of the module.
    has_submissions: bool
    # A step whose last attempt was rejected and not resubmitted yet.
    has_unresolved_return: bool


class StudentAnalytics(StudentInfo):
    lag: Lag
    # When the student last sent anything in the course; the frontend shows
    # it as "today", "yesterday", "N days ago" in the viewer's time zone.
    last_submission_at: datetime | None
    modules: list[StudentModule]


class CourseAnalytics(BaseModel):
    course_id: int
    group_id: int
    students_total: int
    modules: list[ModuleStats]
    students: list[StudentAnalytics]


class StepColumn(BaseModel):
    step_id: int
    # 1-based number of the step within the module.
    position: int
    type: str
    title: str
    max_score: int


class StepCell(BaseModel):
    step_id: int
    # not_started | checking | failed | attempts_exhausted | partial | passed
    state: str
    earned: float
    max_score: int
    completed: bool
    attempts: int
    # Null: no graded first attempt yet, or theory.
    first_attempt_solved: bool | None
    has_unresolved_return: bool
    last_submission_at: datetime | None


class StudentSteps(StudentInfo):
    steps: list[StepCell]


class ModuleAnalytics(BaseModel):
    course_id: int
    module: ModuleStats
    steps: list[StepColumn]
    students: list[StudentSteps]
