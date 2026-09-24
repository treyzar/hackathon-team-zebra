import enum
from typing import Literal

from pydantic import Field, model_validator

from config import settings as app_settings
from steps.base import CommonSettings, GradeResult, Grading, RichText, Schema, StepType
from steps.registry import register

Language = Literal["python3"]
_MAX_SHOWN_OUTPUT = 4096


class Sample(Schema):
    """Example shown to the student: always inline."""

    input: str = Field(default="", max_length=1_000_000)
    output: str = Field(default="", max_length=1_000_000)


class TestCase(Sample):
    """Hidden test. Small data is inline; large data is an uploaded file
    (purpose answer_key) referenced by id instead of the inline text."""

    input_file: int | None = None
    output_file: int | None = None

    @model_validator(mode="after")
    def _one_source(self):
        if self.input_file is not None and self.input:
            raise ValueError("Set either input or input_file, not both")
        if self.output_file is not None and self.output:
            raise ValueError("Set either output or output_file, not both")
        return self


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
    samples: list[Sample] = Field(default=[], max_length=20)


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

    def authored_files(self, content, answer_key):
        return [
            file_id
            for g in answer_key.test_groups
            for t in g.tests
            for file_id in (t.input_file, t.output_file)
            if file_id is not None
        ]

    def check_authored_files(self, content, answer_key, files):
        max_input = app_settings.test_input_max_mb * 1024 * 1024
        max_output = app_settings.judge_max_output_kb * 1024
        max_total = app_settings.test_files_total_mb * 1024 * 1024
        if sum(files[i].size for i in set(files)) > max_total:
            raise ValueError(
                f"Test files together exceed {app_settings.test_files_total_mb} MB"
            )
        for g in answer_key.test_groups:
            for t in g.tests:
                for file_id, limit in (
                    (t.input_file, max_input),
                    (t.output_file, max_output),
                ):
                    if file_id is None:
                        continue
                    f = files[file_id]
                    # Content files are readable by every student.
                    if f.purpose != "answer_key":
                        raise ValueError(
                            f"Test file {file_id} must be uploaded with purpose answer_key"
                        )
                    if f.size > limit:
                        raise ValueError(
                            f"Test file {file_id} is larger than {limit // 1024} KB"
                        )

    async def run_tests(
        self, judge, files, content, answer_key, settings, answer, max_score
    ):
        async def text(inline: str, file_id: int | None) -> str:
            return inline if file_id is None else await files.text(file_id)

        cases = [(t.input, t.output) for t in content.samples]
        for g in answer_key.test_groups:
            for t in g.tests:
                cases.append(
                    (
                        await text(t.input, t.input_file),
                        await text(t.output, t.output_file),
                    )
                )
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
