from typing import Literal

from steps.base import CommonSettings, GradeResult, Grading, RichText, Schema, StepType
from steps.registry import register


class TheoryContent(Schema):
    body: RichText


class TheorySettings(CommonSettings):
    grading: Literal[Grading.NONE] = Grading.NONE


@register
class Theory(StepType):
    key = "theory"
    content_model = TheoryContent
    settings_model = TheorySettings
    fixed_max_score = 0

    def check(self, content, answer_key, settings, answer, max_score):
        return GradeResult(score=0)
