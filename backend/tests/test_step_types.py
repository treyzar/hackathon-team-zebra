"""Step types in isolation: no database needed."""

import uuid

import pytest
from pydantic import TypeAdapter, ValidationError

from steps import StepPayload
from steps.base import FileInfo
from steps.registry import all_types, get_type

payload = TypeAdapter(StepPayload)
A, B, C = (str(uuid.uuid4()) for _ in range(3))
DOC = {"type": "doc", "content": []}


def choice(type_="single_choice", key=None, **settings):
    return {
        "type": type_,
        "max_score": 10,
        "content": {
            "question": DOC,
            "options": [
                {"id": A, "text": "a"},
                {"id": B, "text": "b"},
                {"id": C, "text": "c"},
            ],
        },
        "answer_key": key or {"correct": A},
        "settings": settings,
    }


def program(groups, **settings):
    return {
        "type": "programming",
        "max_score": 10,
        "content": {"statement": DOC},
        "answer_key": {"test_groups": groups},
        "settings": settings,
    }


def test_all_types_registered():
    assert set(all_types()) == {
        "theory",
        "single_choice",
        "multiple_choice",
        "free_text",
        "programming",
    }


def test_defaults_are_filled():
    p = payload.validate_python(choice())
    assert p.settings.grading == "auto"
    assert p.settings.max_attempts is None
    assert p.settings.show_answer == "never"


def test_unknown_correct_option_rejected():
    with pytest.raises(ValidationError, match="Unknown option id"):
        payload.validate_python(choice(key={"correct": str(uuid.uuid4())}))


def test_grading_mode_must_be_supported_by_type():
    with pytest.raises(ValidationError):
        payload.validate_python(choice(grading="manual"))


def test_theory_forces_zero_score():
    p = payload.validate_python(
        {"type": "theory", "max_score": 5, "content": {"body": DOC}}
    )
    assert p.max_score == 0


def test_extra_fields_rejected():
    data = choice()
    data["content"]["surprise"] = 1
    with pytest.raises(ValidationError):
        payload.validate_python(data)


@pytest.mark.parametrize(
    ("picked", "scoring", "expected"),
    [
        ([A, B], "all_or_nothing", 10),
        ([A], "all_or_nothing", 0),
        ([A], "partial", 5),
        ([A, C], "partial", 0),  # one right, one wrong
        ([A, B, C], "partial", 5),  # picking everything is penalized
    ],
)
def test_multiple_choice_scoring(picked, scoring, expected):
    p = payload.validate_python(
        choice("multiple_choice", key={"correct": [A, B]}, scoring=scoring)
    )
    t = get_type("multiple_choice")
    answer = t.answer_model.model_validate({"option_ids": picked})
    assert t.check(p.content, p.answer_key, p.settings, answer, 10).score == expected


def test_per_group_points_must_sum_to_max_score():
    groups = [{"name": "g", "points": 3, "tests": [{"input": "", "output": ""}]}]
    with pytest.raises(ValidationError, match="must equal max_score"):
        payload.validate_python(program(groups, scoring="per_group"))


def test_tests_required_unless_manual():
    with pytest.raises(ValidationError, match="at least one test"):
        payload.validate_python(program([]))
    assert payload.validate_python(program([], grading="manual"))


async def test_programming_per_group(local_judge):
    groups = [
        {"name": "small", "points": 4, "tests": [{"input": "2\n", "output": "4"}]},
        {"name": "big", "points": 6, "tests": [{"input": "-3\n", "output": "9"}]},
    ]
    p = payload.validate_python(program(groups, scoring="per_group"))
    t = get_type("programming")
    # Wrong for negative numbers: only the first group passes.
    code = "n = int(input())\nprint(n * n if n > 0 else 0)"
    answer = t.answer_model.model_validate({"code": code})
    result = await t.run_tests(
        local_judge, NoFiles(), p.content, p.answer_key, p.settings, answer, 10
    )
    assert result.score == 4
    assert [g["passed"] for g in result.details["groups"]] == [True, False]
    # Hidden tests expose verdicts only.
    assert set(result.details["groups"][1]["tests"][0]) == {"verdict", "time"}


def test_reveal_hides_programming_tests():
    groups = [{"name": "g", "points": 0, "tests": [{"input": "1", "output": "1"}]}]
    data = program(groups)
    data["answer_key"]["reference_solution"] = "print(input())"
    p = payload.validate_python(data)
    assert get_type("programming").reveal(p.answer_key) == {
        "reference_solution": "print(input())"
    }


class NoFiles:
    async def text(self, file_id):
        raise AssertionError("no files expected")


class DictFiles:
    def __init__(self, files):
        self.files, self.read = files, []

    async def text(self, file_id):
        self.read.append(file_id)
        return self.files[file_id]


def file_test(**kw):
    return {"name": "big", "points": 10, "tests": [kw]}


def test_test_case_has_one_source():
    with pytest.raises(ValidationError, match="either input or input_file"):
        payload.validate_python(program([file_test(input="1", input_file=5)]))
    with pytest.raises(ValidationError, match="either output or output_file"):
        payload.validate_python(program([file_test(output="1", output_file=5)]))


def test_samples_cannot_reference_files():
    data = program([file_test(input="1", output="1")])
    data["content"]["samples"] = [{"input": "1", "output": "1", "input_file": 3}]
    with pytest.raises(ValidationError):
        payload.validate_python(data)


def test_authored_files_listed_and_checked():
    t = get_type("programming")
    p = payload.validate_python(program([file_test(input_file=1, output_file=2)]))
    assert t.authored_files(p.content, p.answer_key) == [1, 2]

    def infos(purpose="answer_key", out_size=10):
        return {
            1: FileInfo(1, "text/plain", 10, purpose),
            2: FileInfo(2, "text/plain", out_size, purpose),
        }

    t.check_authored_files(p.content, p.answer_key, infos())
    # Content files are readable by students: hidden tests must not be there.
    with pytest.raises(ValueError, match="purpose answer_key"):
        t.check_authored_files(p.content, p.answer_key, infos("content"))
    # Expected output must fit into Judge0's output limit.
    with pytest.raises(ValueError, match="larger than 4096 KB"):
        t.check_authored_files(p.content, p.answer_key, infos(out_size=5 * 2**20))


def test_total_size_of_test_files_limited(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "test_files_total_mb", 1)
    t = get_type("programming")
    p = payload.validate_python(program([file_test(input_file=1, output_file=2)]))
    big = {i: FileInfo(i, "text/plain", 600 * 1024, "answer_key") for i in (1, 2)}
    with pytest.raises(ValueError, match="together exceed 1 MB"):
        t.check_authored_files(p.content, p.answer_key, big)


async def test_programming_reads_test_files(local_judge):
    p = payload.validate_python(
        program([file_test(input_file=1, output_file=2)], scoring="per_group")
    )
    t = get_type("programming")
    files = DictFiles({1: "7\n", 2: "49\n"})
    answer = t.answer_model.model_validate({"code": "print(int(input()) ** 2)"})
    result = await t.run_tests(
        local_judge, files, p.content, p.answer_key, p.settings, answer, 10
    )
    assert result.score == 10
    assert files.read == [1, 2]


def test_free_text_reference_files_must_be_private():
    t = get_type("free_text")
    p = payload.validate_python(
        {
            "type": "free_text",
            "content": {"question": DOC},
            "answer_key": {"files": [4]},
        }
    )
    assert t.authored_files(p.content, p.answer_key) == [4]
    ok = {4: FileInfo(4, "image/png", 1, "answer_key")}
    t.check_authored_files(p.content, p.answer_key, ok)
    with pytest.raises(ValueError, match="purpose answer_key"):
        t.check_authored_files(
            p.content, p.answer_key, {4: FileInfo(4, "image/png", 1, "content")}
        )
