"""Manual review by a checklist: met criteria add up to the score."""

import json

import pytest
from conftest import requires_db
from pydantic import TypeAdapter, ValidationError
from test_api import add_step, free_text, single_choice, submit

from steps import StepPayload

payload = TypeAdapter(StepPayload)
CHECKLIST = [
    {"id": "plan", "text": "Есть план решения", "points": 2, "hint": "Хотя бы 3 шага"},
    {"id": "works", "text": "Программа работает", "points": 3},
]


def essay(checklist=CHECKLIST, **settings):
    step = free_text()
    step["settings"] = {"checklist": checklist, **settings}
    return step


# --- authoring ---------------------------------------------------------------


def test_checklist_is_part_of_settings():
    p = payload.validate_python(essay())
    assert [(i.id, i.points, i.hint) for i in p.settings.checklist] == [
        ("plan", 2, "Хотя бы 3 шага"),
        ("works", 3, None),
    ]
    # Without a checklist nothing changes.
    assert payload.validate_python(free_text()).settings.checklist == []


@pytest.mark.parametrize(
    ("step", "error"),
    [
        (essay(CHECKLIST[:1]), "must add up to max_score"),
        (essay([CHECKLIST[0], {**CHECKLIST[1], "id": "plan"}]), "must be unique"),
        (
            {**single_choice(), "settings": {"checklist": CHECKLIST}},
            "grading by a curator",
        ),
    ],
)
def test_checklist_rules(step, error):
    if step["type"] == "single_choice":
        step["max_score"] = 5
    with pytest.raises(ValidationError, match=error):
        payload.validate_python(step)


# --- review -------------------------------------------------------------------


async def review(client, headers, sub_id, **body):
    return await client.post(
        f"/review/submissions/{sub_id}",
        json={"verdict": "accepted", **body},
        headers=headers,
    )


@requires_db
async def test_score_from_met_criteria(client, admin, course, groups_setup):
    (_, curator, _, student), _ = groups_setup
    step_id = await add_step(client, admin, course[1], essay())
    sub_id = (await submit(client, student, step_id, {"text": "x"})).json()["id"]

    detail = (await client.get(f"/review/submissions/{sub_id}", headers=curator)).json()
    # The curator sees the criteria with hints.
    assert detail["settings"]["checklist"][0]["hint"] == "Хотя бы 3 шага"
    assert detail["review_checklist"] is None

    r = await review(client, curator, sub_id, checked=["works"], comment="Без плана")
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["score"]) == ("accepted", 3)
    assert r.json()["review_checklist"] == ["works"]

    # The student gets the score and the comment, never the criteria.
    mine = (await client.get(f"/submissions/{sub_id}", headers=student)).json()
    assert (mine["score"], mine["review_comment"]) == (3, "Без плана")
    step_view = (await client.get(f"/steps/{step_id}", headers=student)).json()
    for text in ("Есть план решения", "Программа работает", "Хотя бы 3 шага"):
        assert text not in str(mine) and text not in str(step_view)
    assert "review_checklist" not in mine and "checklist" not in str(step_view)


@requires_db
async def test_all_and_nothing(client, admin, course, groups_setup, make_user):
    (_, curator, _, student), _ = groups_setup
    step_id = await add_step(client, admin, course[1], essay())
    sub_id = (await submit(client, student, step_id, {"text": "x"})).json()["id"]
    r = await review(client, curator, sub_id, verdict="rejected", checked=[])
    assert (r.json()["status"], r.json()["score"]) == ("rejected", 0)

    sub_id = (await submit(client, student, step_id, {"text": "y"})).json()["id"]
    # Order and repeats do not matter; the stored order is the checklist's.
    r = await review(client, curator, sub_id, checked=["works", "plan", "works"])
    assert (r.json()["score"], r.json()["review_checklist"]) == (5, ["plan", "works"])


@requires_db
async def test_invalid_reviews(client, admin, course, groups_setup):
    (_, curator, _, student), _ = groups_setup
    with_list = await add_step(client, admin, course[1], essay())
    without = await add_step(client, admin, course[1], free_text())
    sub = (await submit(client, student, with_list, {"text": "x"})).json()["id"]
    plain = (await submit(client, student, without, {"text": "x"})).json()["id"]

    for body in (
        {},
        {"score": 5},
        {"checked": ["works"], "score": 3},
        {"checked": ["nope"]},
    ):
        r = await review(client, curator, sub, **body)
        assert r.status_code == 422, body
    assert (await review(client, curator, plain, checked=[])).status_code == 422
    # Nothing was saved by the failed attempts.
    detail = (await client.get(f"/review/submissions/{sub}", headers=curator)).json()
    assert (detail["status"], detail["review_checklist"]) == ("pending_review", None)


@requires_db
async def test_checklist_overrides_tests(
    client, admin, course, groups_setup, local_judge
):
    from test_api import programming
    from test_worker import drain

    (_, curator, _, student), _ = groups_setup
    step = programming(grading="tests_and_review")
    step["settings"]["checklist"] = [
        {"id": "style", "text": "Код читаемый", "points": 4},
        {"id": "edge", "text": "Учтены крайние случаи", "points": 6},
    ]
    step_id = await add_step(client, admin, course[1], step)
    sub_id = (
        await submit(client, student, step_id, {"code": "print(int(input()) ** 2)"})
    ).json()["id"]
    await drain(local_judge)
    detail = (await client.get(f"/review/submissions/{sub_id}", headers=curator)).json()
    assert (detail["status"], detail["auto_score"]) == ("pending_review", 10)

    r = await review(client, curator, sub_id, checked=["style"])
    assert r.json()["score"] == 4


# --- export / import ---------------------------------------------------------


@requires_db
async def test_export_and_import_keep_the_checklist(client, admin, course):
    await add_step(client, admin, course[1], essay())
    exported = await client.get(f"/admin/courses/{course[0]}/export", headers=admin[1])
    [step] = exported.json()["course"]["modules"][0]["steps"]
    assert step["payload"]["settings"]["checklist"] == [
        {**CHECKLIST[0]},
        {**CHECKLIST[1], "hint": None},
    ]

    imported = await client.post(
        "/admin/courses/import",
        files={"file": ("c.json", exported.content, "application/json")},
        headers=admin[1],
    )
    assert imported.status_code == 201, imported.text
    again = await client.get(
        f"/admin/courses/{imported.json()['course_id']}/export", headers=admin[1]
    )
    [copy] = again.json()["course"]["modules"][0]["steps"]
    assert (
        copy["payload"]["settings"]["checklist"]
        == step["payload"]["settings"]["checklist"]
    )

    # A broken checklist in a file is rejected like in the editor.
    document = exported.json()
    document["course"]["slug"] = "other"
    document["course"]["modules"][0]["steps"][0]["payload"]["settings"]["checklist"][0][
        "points"
    ] = 1
    r = await client.post(
        "/admin/courses/import",
        files={"file": ("bad.json", json.dumps(document), "application/json")},
        headers=admin[1],
    )
    assert r.status_code == 422, r.text


def test_pdf_shows_the_checklist_only_with_answers():
    from types import SimpleNamespace

    from courses.pdf_export import _render_step_pdf

    p = payload.validate_python(essay())
    step = SimpleNamespace(type="free_text", is_hidden=False)
    rev = SimpleNamespace(max_score=5)
    with_answers = _render_step_pdf(step, rev, p, "1.1", {}, True)
    assert "Чек-лист проверки" in with_answers
    assert "Есть план решения — 2 б." in with_answers
    assert "Хотя бы 3 шага" in with_answers
    without = _render_step_pdf(step, rev, p, "1.1", {}, False)
    assert "Есть план решения" not in without and "Хотя бы 3 шага" not in without
