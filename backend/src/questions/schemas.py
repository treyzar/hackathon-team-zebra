from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from questions.models import QuestionVisibility


def _not_blank(value: str | None) -> str | None:
    if value is not None and not value.strip():
        raise ValueError("Must not be empty")
    return value


class QuestionIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"text": "Почему во втором тесте ответ 0?"}]}
    )
    text: str = Field(min_length=1, max_length=5000)

    _check = field_validator("text")(_not_blank)


class QuestionUpdate(BaseModel):
    """Only the fields that are sent change."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"answer": "Нуль — тоже чётное число.", "visibility": "group"},
                {"visibility": "private"},
            ]
        }
    )
    answer: str | None = Field(default=None, min_length=1, max_length=10_000)
    visibility: QuestionVisibility | None = None

    _check = field_validator("answer")(_not_blank)

    @model_validator(mode="after")
    def _something(self):
        if not self.model_fields_set:
            raise ValueError("Send an answer or a visibility")
        if "answer" in self.model_fields_set and self.answer is None:
            raise ValueError("The answer cannot be removed")
        return self


class StudentQuestion(BaseModel):
    """A question as a student sees it: other students' names are hidden."""

    id: int
    step_id: int
    text: str
    created_at: datetime
    is_mine: bool
    visibility: QuestionVisibility
    answer: str | None
    answered_at: datetime | None


class StaffQuestion(BaseModel):
    id: int
    step_id: int
    course_id: int
    course_title: str
    module_title: str
    author_id: int
    author_username: str
    author_name: str
    author_surname: str
    author_patronymic: str
    text: str
    created_at: datetime
    answer: str | None
    answered_by: int | None
    answered_at: datetime | None
    visibility: QuestionVisibility
    # Group the question is open to, for visibility "group".
    group_id: int | None
    # False for a public question of another curator's group: read only.
    can_answer: bool
    # How long an unanswered question has waited; null once answered.
    waiting_seconds: int | None
