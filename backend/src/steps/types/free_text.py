from typing import Literal

from pydantic import Field, model_validator

from steps.base import CommonSettings, Grading, RichText, Schema, StepType
from steps.registry import register


class FreeTextContent(Schema):
    question: RichText
    # The answer must contain text / at least this many files, e.g. a photo.
    require_text: bool = False
    min_files: int = Field(default=0, ge=0, le=10)
    max_files: int = Field(default=0, ge=0, le=10)
    # Empty list means any type is allowed.
    allowed_mime: list[str] = []

    @model_validator(mode="after")
    def _files_range(self):
        if self.min_files > self.max_files:
            raise ValueError("min_files cannot be greater than max_files")
        return self


class FreeTextKey(Schema):
    """Reference answer / criteria shown to the curator."""

    reference: RichText | None = None
    criteria: str | None = Field(default=None, max_length=10_000)
    files: list[int] = []


class FreeTextSettings(CommonSettings):
    grading: Literal[Grading.MANUAL] = Grading.MANUAL


class FreeTextAnswer(Schema):
    text: str = Field(default="", max_length=20_000)
    files: list[int] = Field(default=[], max_length=10)


@register
class FreeText(StepType):
    key = "free_text"
    content_model = FreeTextContent
    answer_key_model = FreeTextKey
    settings_model = FreeTextSettings
    answer_model = FreeTextAnswer

    def validate_answer(self, content, answer):
        if not answer.text.strip() and not answer.files:
            raise ValueError("Answer is empty")
        if content.require_text and not answer.text.strip():
            raise ValueError("The answer must contain text")
        if len(answer.files) < content.min_files:
            raise ValueError(f"Attach at least {content.min_files} file(s)")

    def answer_files(self, answer):
        return answer.files

    def authored_files(self, content, answer_key):
        return answer_key.files

    def check_authored_files(self, content, answer_key, files):
        # Reference files are for curators, never for students.
        for f in files.values():
            if f.purpose != "answer_key":
                raise ValueError(
                    f"Reference file {f.id} must be uploaded with purpose answer_key"
                )

    def reveal(self, answer_key):
        # Criteria and reference files are for curators only.
        reference = answer_key.reference
        return {"reference": reference.model_dump(mode="json") if reference else None}

    def check_files(self, content, files):
        if len(files) > content.max_files:
            raise ValueError(f"At most {content.max_files} files allowed")
        if content.allowed_mime:
            for f in files:
                if f.mime not in content.allowed_mime:
                    raise ValueError(f"File type {f.mime} is not allowed")
