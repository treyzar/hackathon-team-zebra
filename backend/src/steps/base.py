"""Contract every step type implements.

A step type is a single module in ``steps/types`` that subclasses ``StepType``
and registers itself. Everything else (authoring API, submissions, review,
judge worker) talks to types only through this interface, so adding a new type
never requires touching the rest of the code.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from judge import JudgeClient


class Grading(enum.StrEnum):
    NONE = "none"  # nothing to check (theory)
    AUTO = "auto"  # checked synchronously while handling the request
    TESTS = "tests"  # checked in background by the judge worker
    TESTS_AND_REVIEW = "tests_and_review"  # judge first, then a curator
    MANUAL = "manual"  # checked by a curator only

    @property
    def uses_tests(self) -> bool:
        return self in (Grading.TESTS, Grading.TESTS_AND_REVIEW)

    @property
    def uses_review(self) -> bool:
        return self in (Grading.TESTS_AND_REVIEW, Grading.MANUAL)


class ShowAnswer(enum.StrEnum):
    NEVER = "never"
    AFTER_WRONG = "after_wrong"
    AFTER_ATTEMPTS_EXHAUSTED = "after_attempts_exhausted"
    AFTER_SOLVED = "after_solved"


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Empty(Schema):
    pass


class RichText(BaseModel):
    """TipTap / ProseMirror JSON document. Rendered by the frontend."""

    model_config = ConfigDict(extra="allow")
    type: str = "doc"
    content: list[dict[str, Any]] = []


class ChecklistItem(Schema):
    """One criterion a curator marks as met; its points add up to the score."""

    # Stable id: reviews store the ids of met criteria.
    id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=500)
    points: float = Field(ge=0, le=1000)
    # A tip for the curator on how to judge it.
    hint: str | None = Field(default=None, max_length=2000)


class CommonSettings(Schema):
    """Settings shared by every step type.

    A type narrows ``grading`` to the modes it supports by redeclaring it
    as a ``Literal`` in its own settings model, and adds its own fields.
    """

    grading: Grading
    max_attempts: int | None = Field(default=None, ge=1)
    show_answer: ShowAnswer = ShowAnswer.NEVER
    # Criteria a curator checks off instead of typing a score; only for steps
    # a curator reviews. Settings never reach students as a whole, so neither
    # do the criteria.
    checklist: list[ChecklistItem] = Field(default=[], max_length=50)

    @model_validator(mode="after")
    def _checklist_ids(self):
        ids = [item.id for item in self.checklist]
        if len(set(ids)) != len(ids):
            raise ValueError("Checklist item ids must be unique")
        return self


class TestFiles(Protocol):
    """Access to uploaded files (e.g. large tests) while grading."""

    async def text(self, file_id: int) -> str: ...


@dataclass
class GradeResult:
    score: float
    details: dict[str, Any] = field(default_factory=dict)


class StepType:
    key: ClassVar[str]
    # What the author fills in and the student sees.
    content_model: ClassVar[type[Schema]]
    # Correct answer / tests / reference. Never sent to students unless
    # the step's show_answer policy allows ``reveal``.
    answer_key_model: ClassVar[type[Schema]] = Empty
    settings_model: ClassVar[type[CommonSettings]]
    # What the student submits.
    answer_model: ClassVar[type[Schema]] = Empty
    # Bump together with ``upgrade`` when the stored JSON format changes.
    schema_version: ClassVar[int] = 1
    # Types without a score (theory) force max_score to this value.
    fixed_max_score: ClassVar[int | None] = None

    def validate(self, content: Any, answer_key: Any, settings: Any, max_score: int):
        """Cross-field checks of an authored step. Raise ValueError."""

    def validate_answer(self, content: Any, answer: Any) -> None:
        """Checks of a student answer against the step. Raise ValueError."""

    def answer_files(self, answer: Any) -> list[int]:
        """Ids of uploaded files the answer references."""
        return []

    def check_files(self, content: Any, files: list[FileInfo]) -> None:
        """Checks of the attached files' count/types. Raise ValueError."""
        if files:
            raise ValueError("This step does not accept files")

    def authored_files(self, content: Any, answer_key: Any) -> list[int]:
        """Ids of uploaded files the authored step references."""
        return []

    def check_authored_files(
        self, content: Any, answer_key: Any, files: dict[int, FileInfo]
    ) -> None:
        """Checks of those files (purpose, size). Raise ValueError."""

    def check(
        self, content: Any, answer_key: Any, settings: Any, answer: Any, max_score: int
    ) -> GradeResult:
        """Synchronous grading, required for Grading.AUTO."""
        raise NotImplementedError

    async def run_tests(
        self,
        judge: JudgeClient,
        files: TestFiles,
        content: Any,
        answer_key: Any,
        settings: Any,
        answer: Any,
        max_score: int,
    ) -> GradeResult:
        """Background grading, required for Grading.TESTS*."""
        raise NotImplementedError

    def explain(
        self, content: Any, answer_key: Any, answer: Any
    ) -> dict[str, Any] | None:
        """Detailed feedback on one answer that gives the correct answer away
        (e.g. which options were right). Shown to the student only when the
        step's show_answer policy allows, like ``reveal``."""
        return None

    def reveal(self, answer_key: Any) -> dict[str, Any]:
        """Part of the answer key a student may see when allowed."""
        return answer_key.model_dump(mode="json")

    def upgrade(self, data: dict[str, Any], from_version: int) -> dict[str, Any]:
        """Migrate a stored revision {content, answer_key, settings} in place."""
        return data


@dataclass
class FileInfo:
    id: int
    mime: str
    size: int
    purpose: str = ""
