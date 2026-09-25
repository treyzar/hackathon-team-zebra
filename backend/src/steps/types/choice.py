import enum
from typing import Literal
from uuid import UUID

from pydantic import Field

from steps.base import CommonSettings, GradeResult, Grading, RichText, Schema, StepType
from steps.registry import register


class Option(Schema):
    # Stable id: the answer key refers to it, so reordering is safe.
    id: UUID
    text: str = Field(min_length=1, max_length=2000)


class ChoiceContent(Schema):
    question: RichText
    options: list[Option] = Field(min_length=2, max_length=50)


def _check_options(content: ChoiceContent, ids: list[UUID]) -> None:
    known = {o.id for o in content.options}
    if len(known) != len(content.options):
        raise ValueError("Option ids must be unique")
    if not set(ids) <= known:
        raise ValueError("Unknown option id")


# --- single choice ---------------------------------------------------------


class SingleChoiceKey(Schema):
    correct: UUID


class SingleChoiceSettings(CommonSettings):
    grading: Literal[Grading.AUTO] = Grading.AUTO


class SingleChoiceAnswer(Schema):
    option_id: UUID


@register
class SingleChoice(StepType):
    key = "single_choice"
    content_model = ChoiceContent
    answer_key_model = SingleChoiceKey
    settings_model = SingleChoiceSettings
    answer_model = SingleChoiceAnswer

    def validate(self, content, answer_key, settings, max_score):
        _check_options(content, [answer_key.correct])

    def validate_answer(self, content, answer):
        _check_options(content, [answer.option_id])

    def check(self, content, answer_key, settings, answer, max_score):
        ok = answer.option_id == answer_key.correct
        return GradeResult(score=max_score if ok else 0)


# --- multiple choice -------------------------------------------------------


class Scoring(enum.StrEnum):
    ALL_OR_NOTHING = "all_or_nothing"
    # (right picks - wrong picks) / number of correct options, not below 0,
    # so selecting every option does not earn points.
    PARTIAL = "partial"


class MultipleChoiceKey(Schema):
    correct: list[UUID] = Field(min_length=1)


class MultipleChoiceSettings(CommonSettings):
    grading: Literal[Grading.AUTO] = Grading.AUTO
    scoring: Scoring = Scoring.ALL_OR_NOTHING


class MultipleChoiceAnswer(Schema):
    option_ids: list[UUID]


@register
class MultipleChoice(StepType):
    key = "multiple_choice"
    content_model = ChoiceContent
    answer_key_model = MultipleChoiceKey
    settings_model = MultipleChoiceSettings
    answer_model = MultipleChoiceAnswer

    def validate(self, content, answer_key, settings, max_score):
        _check_options(content, answer_key.correct)
        if len(set(answer_key.correct)) != len(answer_key.correct):
            raise ValueError("Duplicate correct option")

    def validate_answer(self, content, answer):
        _check_options(content, answer.option_ids)

    def check(self, content, answer_key, settings, answer, max_score):
        correct, picked = set(answer_key.correct), set(answer.option_ids)
        right, wrong = len(picked & correct), len(picked - correct)
        # Counts explain the score without telling which options are right.
        details = {
            "correct_picked": right,
            "wrong_picked": wrong,
            "correct_total": len(correct),
        }
        if settings.scoring == Scoring.ALL_OR_NOTHING:
            score = max_score if picked == correct else 0
        else:
            fraction = max(0.0, (right - wrong) / len(correct))
            score = round(max_score * fraction, 2)
        return GradeResult(score=score, details=details)

    def explain(self, content, answer_key, answer):
        correct, picked = set(answer_key.correct), set(answer.option_ids)
        return {
            "options": [
                {"id": str(o.id), "picked": o.id in picked, "correct": o.id in correct}
                for o in content.options
            ]
        }
