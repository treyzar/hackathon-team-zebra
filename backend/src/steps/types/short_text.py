import re
from typing import Literal

from pydantic import Field

from steps.base import CommonSettings, GradeResult, Grading, RichText, Schema, StepType
from steps.registry import register

MAX_LENGTH = 500


class ShortTextContent(Schema):
    question: RichText


class ShortTextKey(Schema):
    # Auto grading: the answer must match one of these. Manual grading: a
    # reference for the curator (may be empty).
    accepted: list[str] = Field(default=[], max_length=50)
    case_sensitive: bool = False


class ShortTextSettings(CommonSettings):
    grading: Literal[Grading.AUTO, Grading.MANUAL] = Grading.AUTO


class ShortTextAnswer(Schema):
    text: str = Field(min_length=1, max_length=MAX_LENGTH)


def _normalize(text: str, case_sensitive: bool) -> str:
    # Extra spaces and letter case are typing slips, not a different answer.
    text = re.sub(r"\s+", " ", text).strip()
    return text if case_sensitive else text.casefold()


@register
class ShortText(StepType):
    key = "short_text"
    content_model = ShortTextContent
    answer_key_model = ShortTextKey
    settings_model = ShortTextSettings
    answer_model = ShortTextAnswer

    def validate(self, content, answer_key, settings, max_score):
        accepted = [a.strip() for a in answer_key.accepted]
        if any(not a or len(a) > MAX_LENGTH for a in accepted):
            raise ValueError(
                f"Accepted answers must be non-empty, at most {MAX_LENGTH} characters"
            )
        if settings.grading == Grading.AUTO and not accepted:
            raise ValueError("Automatic grading needs at least one accepted answer")

    def validate_answer(self, content, answer):
        if not answer.text.strip():
            raise ValueError("Answer is empty")

    def check(self, content, answer_key, settings, answer, max_score):
        cs = answer_key.case_sensitive
        accepted = {_normalize(a, cs) for a in answer_key.accepted}
        ok = _normalize(answer.text, cs) in accepted
        return GradeResult(score=max_score if ok else 0)

    def reveal(self, answer_key):
        return {"accepted": answer_key.accepted}
