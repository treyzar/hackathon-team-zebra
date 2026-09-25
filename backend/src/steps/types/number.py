import enum
import re
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Literal

from pydantic import Field

from steps.base import CommonSettings, GradeResult, Grading, RichText, Schema, StepType
from steps.registry import register


class NumberKind(enum.StrEnum):
    INTEGER = "integer"
    DECIMAL = "decimal"


class NumberContent(Schema):
    question: RichText
    kind: NumberKind = NumberKind.INTEGER
    # Decimal places the answer is compared to; the student sees it to know
    # how to round. Ignored for integers.
    precision: int = Field(default=2, ge=0, le=10)


class NumberKey(Schema):
    value: Decimal = Field(max_digits=30, decimal_places=10)


class NumberSettings(CommonSettings):
    grading: Literal[Grading.AUTO] = Grading.AUTO


class NumberAnswer(Schema):
    # A string, not a float: "0.1" must stay exactly 0.1, and a comma as the
    # decimal separator is accepted.
    value: str = Field(min_length=1, max_length=40)


_INTEGER = re.compile(r"[+-]?\d+")
_DECIMAL = re.compile(r"[+-]?(\d+([.,]\d*)?|[.,]\d+)")


def _parse(content: NumberContent, text: str) -> Decimal:
    text = text.strip().replace(" ", "")
    pattern = _INTEGER if content.kind == NumberKind.INTEGER else _DECIMAL
    if not pattern.fullmatch(text):
        raise ValueError(
            "Enter an integer"
            if content.kind == NumberKind.INTEGER
            else "Enter a number, e.g. 3.14"
        )
    return Decimal(text.replace(",", "."))


def _rounded(content: NumberContent, value: Decimal) -> Decimal:
    places = 0 if content.kind == NumberKind.INTEGER else content.precision
    # Plenty of digits: 30-digit values quantized to 10 places must not trip
    # the default 28-digit context.
    with localcontext(prec=100):
        return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


@register
class Number(StepType):
    key = "number"
    content_model = NumberContent
    answer_key_model = NumberKey
    settings_model = NumberSettings
    answer_model = NumberAnswer

    def validate(self, content, answer_key, settings, max_score):
        value = answer_key.value
        if content.kind == NumberKind.INTEGER and value != value.to_integral_value():
            raise ValueError("The answer of an integer step must be an integer")

    def validate_answer(self, content, answer):
        # A malformed number is a typo, not a wrong answer: 422, no attempt used.
        _parse(content, answer.value)

    def check(self, content, answer_key, settings, answer, max_score):
        # "With precision 2" means both sides rounded to 2 places must match:
        # 3.14159 accepts 3.14 and 3.141, but not 3.15.
        given = _rounded(content, _parse(content, answer.value))
        ok = given == _rounded(content, answer_key.value)
        return GradeResult(score=max_score if ok else 0)

    def reveal(self, answer_key):
        return {"value": str(answer_key.value)}
