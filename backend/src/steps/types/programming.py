import enum
from typing import Literal

from pydantic import Field

from steps.base import CommonSettings, GradeResult, Grading, RichText, Schema, StepType
from steps.registry import register

Language = Literal["python3"]
_MAX_SHOWN_OUTPUT = 4096


class TestCase(Schema):
    input: str = Field(default="", max_length=1_000_000)
    output: str = Field(default="", max_length=1_000_000)


class TestGroup(Schema):
    name: str = Field(min_length=1, max_length=200)
    points: int = Field(default=0, ge=0)
    tests: list[TestCase] = Field(max_length=200)


class ProgrammingContent(Schema):
    statement: RichText
    language: Language = "python3"
    time_limit_ms: int = Field(default=2000, ge=100, le=15_000)
    memory_limit_mb: int = Field(default=256, ge=16, le=512)
    template: str = Field(default="", max_length=65_536)
    # Shown to the student; run for feedback but not scored.
    samples: list[TestCase] = Field(default=[], max_length=20)


class ProgrammingKey(Schema):
    test_groups: list[TestGroup] = Field(default=[], max_length=50)
    reference_solution: str | None = Field(default=None, max_length=65_536)


class Scoring(enum.StrEnum):
    ALL_OR_NOTHING = "all_or_nothing"
    PER_GROUP = "per_group"  # sum of points of fully passed test groups


class ProgrammingSettings(CommonSettings):
    grading: Literal[Grading.TESTS, Grading.TESTS_AND_REVIEW, Grading.MANUAL] = (
        Grading.TESTS
    )
    scoring: Scoring = Scoring.ALL_OR_NOTHING


class ProgrammingAnswer(Schema):
    code: str = Field(min_length=1, max_length=65_536)
    language: Language = "python3"


def _cut(s: str | None) -> str | None:
    if s is None or len(s) <= _MAX_SHOWN_OUTPUT:
        return s
    return s[:_MAX_SHOWN_OUTPUT] + "\n…(truncated)"


@register
class Programming(StepType):
    key = "programming"
    content_model = ProgrammingContent
    answer_key_model = ProgrammingKey
    settings_model = ProgrammingSettings
    answer_model = ProgrammingAnswer

    def validate(self, content, answer_key, settings, max_score):
        if not settings.grading.uses_tests:
            return
        groups = answer_key.test_groups
        if not groups or any(not g.tests for g in groups):
            raise ValueError("Every test group needs at least one test")
        if settings.scoring == Scoring.PER_GROUP:
            total = sum(g.points for g in groups)
            if total != max_score:
                raise ValueError(
                    f"Sum of group points ({total}) must equal max_score ({max_score})"
                )

    async def run_tests(self, judge, content, answer_key, settings, answer, max_score):
        cases = [(t.input, t.output) for t in content.samples]
        for g in answer_key.test_groups:
            cases += [(t.input, t.output) for t in g.tests]
        runs = await judge.run(
            answer.code,
            cases,
            time_limit_s=content.time_limit_ms / 1000,
            memory_limit_kb=content.memory_limit_mb * 1024,
        )

        samples = [
            {
                "input": t.input,
                "expected": t.output,
                "verdict": r.verdict,
                "stdout": _cut(r.stdout),
                "stderr": _cut(r.stderr),
                "time": r.time,
            }
            for t, r in zip(content.samples, runs, strict=False)
        ]
        pos = len(content.samples)
        groups, score, all_passed = [], 0.0, True
        for g in answer_key.test_groups:
            group_runs = runs[pos : pos + len(g.tests)]
            pos += len(g.tests)
            passed = all(r.verdict == "ok" for r in group_runs)
            all_passed &= passed
            earned = g.points if passed and settings.scoring == Scoring.PER_GROUP else 0
            score += earned
            groups.append(
                {
                    "name": g.name,
                    "points": g.points,
                    "passed": passed,
                    "earned": earned,
                    # Hidden tests: verdicts only, never input/output.
                    "tests": [
                        {"verdict": r.verdict, "time": r.time} for r in group_runs
                    ],
                }
            )
        if settings.scoring == Scoring.ALL_OR_NOTHING:
            score = max_score if all_passed else 0
        return GradeResult(score=score, details={"samples": samples, "groups": groups})

    def reveal(self, answer_key):
        # Hidden tests are never revealed.
        return {"reference_solution": answer_key.reference_solution}
