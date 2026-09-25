"""Languages of programming steps: mapping to Judge0, authoring, answers."""

import pytest
from conftest import LocalJudge, requires_db
from pydantic import TypeAdapter, ValidationError
from test_api import add_step, programming, submit
from test_judge import LANGUAGES_113
from test_step_types import DOC, NoFiles, program

from languages import LANGUAGES, resolve_ids
from steps import StepPayload
from steps.registry import get_type, parse_revision

payload = TypeAdapter(StepPayload)
GROUPS = [{"name": "g", "points": 0, "tests": [{"input": "3\n", "output": "9"}]}]


def step(languages=None):
    p = program(GROUPS)
    if languages is not None:
        p["content"]["languages"] = languages
    return payload.validate_python(p)


# --- mapping to Judge0 -----------------------------------------------------


def test_every_language_resolves_in_judge0_113():
    assert resolve_ids(LANGUAGES_113) == {
        "python3": 71,
        "javascript": 93,
        "cpp": 54,
        "csharp": 51,
        "go": 95,
        "pascal": 67,
    }


def test_newest_version_wins_whatever_the_id_order():
    ids = resolve_ids(
        [
            {"id": 5, "name": "Go (1.22.0)"},
            {"id": 9, "name": "Go (1.9.0)"},  # 9 < 22 as numbers, not as text
            {"id": 1, "name": "Python (2.7.17)"},  # Python 2 is not "python3"
        ]
    )
    assert ids == {"go": 5}


def test_language_dropped_by_judge0_is_absent():
    assert "go" not in resolve_ids([{"id": 71, "name": "Python (3.8.1)"}])


# --- authoring -------------------------------------------------------------


def test_default_language_is_python():
    assert step().content.languages == ["python3"]


def test_several_languages_keep_their_order():
    assert step(["cpp", "python3"]).content.languages == ["cpp", "python3"]


@pytest.mark.parametrize(
    "languages", [[], ["python3", "python3"], ["cobol"], ["python3", "go", "rust"]]
)
def test_bad_language_lists_rejected(languages):
    with pytest.raises(ValidationError):
        step(languages)


def test_old_language_field_is_rejected_on_input():
    p = program(GROUPS)
    p["content"]["language"] = "python3"
    with pytest.raises(ValidationError):
        payload.validate_python(p)


def test_revision_saved_with_single_language_is_upgraded():
    content = {"statement": DOC, "language": "python3", "time_limit_ms": 1000}
    parsed = parse_revision(
        "programming",
        content,
        {},
        {"grading": "manual"},
        schema_version=1,
        max_score=1,
    )
    assert parsed.content.languages == ["python3"]


# --- student answers -------------------------------------------------------


@pytest.mark.parametrize(
    ("allowed", "chosen", "error"),
    [
        (["python3"], None, None),
        (["python3"], "python3", None),
        (["python3"], "go", "not allowed"),
        (["cpp", "go"], "go", None),
        (["cpp", "go"], None, "Choose a language"),
        (["cpp", "go"], "python3", "not allowed"),
    ],
)
def test_answer_language_must_be_one_the_step_allows(allowed, chosen, error):
    t = get_type("programming")
    answer = t.answer_model.model_validate({"code": "x", "language": chosen})
    content = step(allowed).content
    if error is None:
        t.validate_answer(content, answer)
    else:
        with pytest.raises(ValueError, match=error):
            t.validate_answer(content, answer)


async def test_code_is_run_in_the_chosen_language():
    seen = []

    class Recording(LocalJudge):
        async def run(self, code, cases, time_limit_s, memory_limit_kb, language):
            seen.append(language)
            return await super().run(code, cases, time_limit_s, memory_limit_kb)

    t = get_type("programming")
    p = step(["cpp", "python3"])
    for chosen, expected in [("python3", "python3"), (None, "cpp")]:
        answer = t.answer_model.model_validate(
            {"code": "print(int(input()) ** 2)", "language": chosen}
        )
        await t.run_tests(
            Recording(), NoFiles(), p.content, p.answer_key, p.settings, answer, 10
        )
        assert seen[-1] == expected  # the first allowed one when not chosen


# --- API (needs TEST_DB_URL) ------------------------------------------------


def multi_language_step():
    s = programming()
    s["content"]["languages"] = ["python3", "cpp"]
    return s


@requires_db
async def test_submission_with_disallowed_language_rejected(
    client, admin, course, make_user
):
    step_id = await add_step(client, admin, course[1], multi_language_step())
    _, h = await make_user()
    for answer in ({"code": "x"}, {"code": "x", "language": "go"}):
        r = await submit(client, h, step_id, answer)
        assert r.status_code == 422, r.text
    r = await submit(client, h, step_id, {"code": "x", "language": "cpp"})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "queued"


@requires_db
async def test_student_sees_allowed_languages_only_in_content(
    client, admin, course, make_user
):
    step_id = await add_step(client, admin, course[1], multi_language_step())
    _, h = await make_user()
    r = await client.get(f"/steps/{step_id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["content"]["languages"] == ["python3", "cpp"]


@requires_db
async def test_languages_endpoint(client, make_user, monkeypatch):
    import languages_api

    class Judge:
        async def language_ids(self):
            return {"python3": 71}

    monkeypatch.setattr(languages_api, "_judge", lambda: Judge())
    _, h = await make_user()
    r = await client.get("/programming/languages", headers=h)
    assert r.status_code == 200, r.text
    got = {i["key"]: i["available"] for i in r.json()}
    assert set(got) == set(LANGUAGES)
    assert got["python3"] is True
    assert got["go"] is False


@requires_db
async def test_languages_endpoint_when_judge0_is_down(client, make_user, monkeypatch):
    import languages_api
    from judge import JudgeError

    class Judge:
        async def language_ids(self):
            raise JudgeError("down")

    monkeypatch.setattr(languages_api, "_judge", lambda: Judge())
    _, h = await make_user()
    r = await client.get("/programming/languages", headers=h)
    assert r.status_code == 200
    assert {i["available"] for i in r.json()} == {None}


@requires_db
async def test_languages_endpoint_needs_login(client):
    r = await client.get("/programming/languages")
    assert r.status_code == 401
