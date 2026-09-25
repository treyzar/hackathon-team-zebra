from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from courses.models import StepAccess
from steps import StepPayload
from steps.base import Grading, RichText, ShowAnswer
from submissions.models import SubmissionStatus

SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class ORM(BaseModel):
    model_config = {"from_attributes": True}


# --- authoring -------------------------------------------------------------


class CourseCreate(BaseModel):
    slug: str = Field(max_length=100, pattern=SLUG)
    title: str = Field(min_length=1, max_length=200)
    description: RichText = RichText()
    step_access: StepAccess = StepAccess.ALL


class CourseUpdate(BaseModel):
    slug: str | None = Field(default=None, max_length=100, pattern=SLUG)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: RichText | None = None
    is_published: bool | None = None
    step_access: StepAccess | None = None


class CourseOut(ORM):
    id: int
    slug: str
    title: str
    description: dict[str, Any]
    is_published: bool
    step_access: StepAccess


class ModuleIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class Order(BaseModel):
    """All live children ids in the new order."""

    ids: list[int]


class StepSave(BaseModel):
    payload: StepPayload
    comment: str | None = Field(default=None, max_length=1000)
    # Correct answer changed: mark earlier submissions as outdated.
    is_breaking: bool = False
    # Revision number the edit is based on (optimistic locking).
    base_revision: int | None = None


class StepFlags(BaseModel):
    is_hidden: bool


class RevisionOut(ORM):
    number: int
    created_at: datetime
    author_id: int | None
    comment: str | None
    is_breaking: bool
    max_score: int
    schema_version: int
    content: dict[str, Any]
    answer_key: dict[str, Any]
    settings: dict[str, Any]


class RevisionSummary(ORM):
    number: int
    created_at: datetime
    author_id: int | None
    comment: str | None
    is_breaking: bool


class AdminStepOut(BaseModel):
    id: int
    module_id: int
    type: str
    position: int
    is_hidden: bool
    revision: RevisionOut


class AdminStepSummary(BaseModel):
    id: int
    type: str
    position: int
    is_hidden: bool
    max_score: int
    revision_number: int


class AdminModuleOut(BaseModel):
    id: int
    title: str
    position: int
    steps: list[AdminStepSummary]


class AdminCourseTree(CourseOut):
    modules: list[AdminModuleOut]


# --- learning --------------------------------------------------------------


class CourseListItem(ORM):
    id: int
    slug: str
    title: str


class StepProgress(BaseModel):
    # none | in_progress | solved | failed
    state: str = "none"
    best_score: float | None = None


class StudentStepSummary(BaseModel):
    id: int
    type: str
    max_score: int
    progress: StepProgress
    # Sequential courses: the previous step is not passed yet.
    locked: bool = False


class StudentModule(BaseModel):
    id: int
    title: str
    steps: list[StudentStepSummary]


class StudentCourse(CourseListItem):
    description: dict[str, Any]
    step_access: StepAccess
    modules: list[StudentModule]


class StudentStep(BaseModel):
    id: int
    course_id: int
    module_id: int
    type: str
    max_score: int
    content: dict[str, Any]
    grading: Grading
    max_attempts: int | None
    show_answer: ShowAnswer
    attempts_used: int
    progress: StepProgress
    answer_available: bool
    # False while a check is running, attempts are used up or the maximum
    # score is reached; the reason is in submit_block_reason.
    can_submit: bool
    submit_block_reason: str | None


class SubmitIn(BaseModel):
    answer: dict[str, Any] = {}


class SubmissionOut(ORM):
    id: int
    step_id: int
    status: SubmissionStatus
    score: float | None
    auto_score: float | None
    answer: dict[str, Any]
    result_details: dict[str, Any]
    is_outdated: bool
    review_comment: str | None
    reviewed_at: datetime | None
    created_at: datetime
