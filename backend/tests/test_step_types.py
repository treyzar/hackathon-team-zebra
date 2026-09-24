"""Step types in isolation: no database needed."""

import uuid

import pytest
from pydantic import TypeAdapter, ValidationError

from steps import StepPayload
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
        local_judge, p.content, p.answer_key, p.settings, answer, 10
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
