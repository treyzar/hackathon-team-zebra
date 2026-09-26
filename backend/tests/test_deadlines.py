"""Deadlines per group: who sets them, inheritance, what students see."""

from datetime import datetime

import pytest
from conftest import requires_db
from test_api import A, B, add_step, free_text, single_choice, submit

pytestmark = requires_db
D1 = "2026-10-01T23:59:00+03:00"
D2 = "2026-10-15T23:59:00+03:00"


def same_time(a, b):
    return datetime.fromisoformat(a) == datetime.fromisoformat(b)


async def put_deadline(client, headers, group_id, step_id, due_at=D1):
    return await client.put(
        f"/groups/{group_id}/deadlines/{step_id}",
        json={"due_at": due_at},
        headers=headers,
    )


async def listing(client, headers, group_id, course_id):
    r = await client.get(
        f"/groups/{group_id}/courses/{course_id}/deadlines", headers=headers
    )
    assert r.status_code == 200, r.text
    return r.json()


def effective(rows):
    """(step_id, due_at or None, inherited) per step."""
    return [
        (
            r["step_id"],
            r["effective"] and r["effective"]["due_at"],
            r["effective"] and r["effective"]["inherited"],
        )
        for r in rows
    ]


async def test_who_may_set_deadlines(client, admin, course, groups_setup):
    (g1, curator1, _, student1), (g2, _, _, _) = groups_setup
    step = await add_step(client, admin, course[1], single_choice())

    r = await put_deadline(client, curator1, g1, step)
    assert r.status_code == 200 and same_time(r.json()["due_at"], D1)
    # Not their group.
    assert (await put_deadline(client, curator1, g2, step)).status_code == 403
    assert (
        await client.delete(f"/groups/{g2}/deadlines/{step}", headers=curator1)
    ).status_code == 403
    assert (
        await client.get(
            f"/groups/{g2}/courses/{course[0]}/deadlines", headers=curator1
        )
    ).status_code == 403
    # Students cannot set deadlines at all.
    assert (await put_deadline(client, student1, g1, step)).status_code == 403
    # Admins can, for any group.
    assert (await put_deadline(client, admin[1], g2, step)).status_code == 200


async def test_curator_lists_own_groups(client, admin, groups_setup):
    (g1, curator1, _, _), (g2, _, _, _) = groups_setup
    mine = (await client.get("/groups", headers=curator1)).json()
    assert [g["id"] for g in mine] == [g1]
    everything = (await client.get("/groups", headers=admin[1])).json()
    assert {g["id"] for g in everything} == {g1, g2}


async def test_deadline_list_includes_step_labels_for_editor(
    client, admin, course, groups_setup
):
    (g1, curator, _, _), _ = groups_setup
    payload = single_choice()
    payload["content"]["question"] = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1, "zebra_title": True},
                "content": [{"type": "text", "text": "Проверка окна"}],
            }
        ],
    }
    step_id = await add_step(client, admin, course[1], payload)
    rows = await listing(client, curator, g1, course[0])
    assert rows[0]["step_id"] == step_id
    assert rows[0]["module_title"] == "Intro"
    assert rows[0]["title"] == "Проверка окна"
    assert isinstance(rows[0]["module_position"], int)
    assert isinstance(rows[0]["step_position"], int)


async def test_earlier_steps_inherit_next_deadline(client, admin, course, groups_setup):
    (g1, curator, _, student), _ = groups_setup
    m2 = (
        await client.post(
            f"/admin/courses/{course[0]}/modules",
            json={"title": "Two"},
            headers=admin[1],
        )
    ).json()["id"]
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    s3 = await add_step(client, admin, m2, single_choice())
    s4 = await add_step(client, admin, m2, single_choice())
    s5 = await add_step(client, admin, m2, single_choice())
    s6 = await add_step(client, admin, m2, single_choice())
    await put_deadline(client, curator, g1, s3, D1)
    await put_deadline(client, curator, g1, s5, D2)

    rows = await listing(client, curator, g1, course[0])
    got = effective(rows)
    assert [s for s, _, _ in got] == [s1, s2, s3, s4, s5, s6]
    # s1, s2 (previous module) take s3's; s4 takes s5's; after s5 — none.
    expected = [(D1, True), (D1, True), (D1, False), (D2, True), (D2, False)]
    for (_, due, inherited), (want, want_inh) in zip(got, expected, strict=False):
        assert same_time(due, want) and inherited == want_inh
    assert got[5][1] is None
    # Only what people set is stored as own.
    assert [r["own"] is not None for r in rows] == [
        False,
        False,
        True,
        False,
        True,
        False,
    ]
    assert rows[0]["effective"]["source_step_id"] == s3

    # The student sees the same, in the course tree and on the step.
    tree = (await client.get(f"/courses/{course[0]}", headers=student)).json()
    shown = [s["deadline"] for m in tree["modules"] for s in m["steps"]]
    assert same_time(shown[1]["due_at"], D1) and shown[1]["inherited"]
    assert shown[5] is None
    step = (await client.get(f"/steps/{s4}", headers=student)).json()
    assert same_time(step["deadline"]["due_at"], D2)
    assert step["deadline"] == {
        **step["deadline"],
        "inherited": True,
        "source_step_id": s5,
    }


async def test_deadlines_are_per_group(client, admin, course, groups_setup, make_user):
    (g1, curator, _, _), (_, _, _, other_student) = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    await put_deadline(client, curator, g1, step)

    other = (await client.get(f"/steps/{step}", headers=other_student)).json()
    assert other["deadline"] is None
    _, loner = await make_user()  # in no group
    assert (await client.get(f"/steps/{step}", headers=loner)).json()[
        "deadline"
    ] is None


async def test_course_deadline_is_fallback_and_can_be_removed(
    client, admin, course, groups_setup, make_user
):
    (g1, curator, _, student), _ = groups_setup
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    url = f"/admin/courses/{course[0]}"

    updated = await client.patch(url, json={"deadline_at": D2}, headers=admin[1])
    assert updated.status_code == 200 and same_time(updated.json()["deadline_at"], D2)
    assert same_time(
        (await client.get(url, headers=admin[1])).json()["deadline_at"], D2
    )

    _, loner = await make_user()
    for headers in (student, loner):
        step = (await client.get(f"/steps/{s2}", headers=headers)).json()
        assert same_time(step["deadline"]["due_at"], D2)
        assert step["deadline"]["source_step_id"] is None

    await put_deadline(client, curator, g1, s1, D1)
    rows = await listing(client, curator, g1, course[0])
    assert same_time(rows[0]["effective"]["due_at"], D1)
    assert rows[0]["effective"]["source_step_id"] == s1
    assert same_time(rows[1]["effective"]["due_at"], D2)
    assert rows[1]["own"] is None

    cleared = await client.patch(url, json={"deadline_at": None}, headers=admin[1])
    assert cleared.status_code == 200 and cleared.json()["deadline_at"] is None
    assert (await client.get(f"/steps/{s2}", headers=student)).json()[
        "deadline"
    ] is None
    assert same_time(
        (await client.get(f"/steps/{s1}", headers=student)).json()["deadline"][
            "due_at"
        ],
        D1,
    )


async def test_course_deadline_requires_timezone(client, admin, course):
    response = await client.patch(
        f"/admin/courses/{course[0]}",
        json={"deadline_at": "2026-10-01T23:59:00"},
        headers=admin[1],
    )
    assert response.status_code == 422


async def test_group_course_deadline_overrides_course_and_respects_access(
    client, admin, course, groups_setup
):
    (g1, curator, _, student), (g2, _, _, other_student) = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    course_url = f"/admin/courses/{course[0]}"
    await client.patch(course_url, json={"deadline_at": D2}, headers=admin[1])
    url = f"/groups/{g1}/courses/{course[0]}/deadline"

    initial = await client.get(url, headers=curator)
    assert initial.status_code == 200 and initial.json()["own"] is None
    assert same_time(initial.json()["effective_due_at"], D2)

    saved = await client.put(url, json={"due_at": D1}, headers=curator)
    assert saved.status_code == 200 and same_time(saved.json()["own"]["due_at"], D1)
    assert same_time(saved.json()["effective_due_at"], D1)
    assert same_time(
        (await client.get(f"/steps/{step}", headers=student)).json()["deadline"][
            "due_at"
        ],
        D1,
    )
    assert same_time(
        (await client.get(f"/steps/{step}", headers=other_student)).json()["deadline"][
            "due_at"
        ],
        D2,
    )

    assert (await client.get(url, headers=other_student)).status_code == 403
    assert (
        await client.put(url, json={"due_at": D2}, headers=other_student)
    ).status_code == 403
    assert (
        await client.put(
            f"/groups/{g2}/courses/{course[0]}/deadline",
            json={"due_at": D1},
            headers=curator,
        )
    ).status_code == 403
    assert (await client.delete(url, headers=other_student)).status_code == 403

    replaced = await client.put(url, json={"due_at": D2}, headers=admin[1])
    assert replaced.status_code == 200 and same_time(
        replaced.json()["own"]["due_at"], D2
    )
    assert (await client.delete(url, headers=curator)).status_code == 204
    after = (await client.get(url, headers=curator)).json()
    assert after["own"] is None and same_time(after["effective_due_at"], D2)
    assert (await client.delete(url, headers=curator)).status_code == 404


async def test_group_course_deadline_validates_course_and_timezone(
    client, admin, course, groups_setup
):
    (g1, curator, _, _), _ = groups_setup
    url = f"/groups/{g1}/courses/{course[0]}/deadline"
    assert (
        await client.put(url, json={"due_at": "2026-10-01T23:59:00"}, headers=curator)
    ).status_code == 422
    assert (
        await client.put(
            f"/groups/{g1}/courses/999999/deadline",
            json={"due_at": D1},
            headers=curator,
        )
    ).status_code == 404


async def test_step_deadline_overrides_group_course_deadline(
    client, admin, course, groups_setup
):
    (g1, curator, _, student), _ = groups_setup
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    await client.put(
        f"/groups/{g1}/courses/{course[0]}/deadline",
        json={"due_at": D2},
        headers=curator,
    )
    await put_deadline(client, curator, g1, s1, D1)
    rows = await listing(client, curator, g1, course[0])
    assert same_time(rows[0]["effective"]["due_at"], D1)
    assert same_time(rows[1]["effective"]["due_at"], D2)

    await client.put(
        f"/groups/{g1}/courses/{course[0]}/deadline",
        json={"due_at": PAST},
        headers=curator,
    )
    late = (await submit(client, student, s2, {"option_id": B})).json()
    assert late["is_late"] and same_time(late["deadline_due_at"], PAST)


async def test_moved_group_deadline_notifies_its_enrolled_students(
    client, admin, course, groups_setup
):
    (g1, curator, _, student), (_, _, _, other_student) = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    url = f"/groups/{g1}/courses/{course[0]}/deadline"

    await client.put(url, json={"due_at": D2}, headers=curator)
    await client.put(url, json={"due_at": D2}, headers=curator)
    mine = (await client.get("/notifications", headers=student)).json()
    changed = [item for item in mine if item["type"] == "deadline_changed"]
    assert len(changed) == 1
    assert changed[0]["payload"]["step_id"] is None
    assert same_time(changed[0]["payload"]["deadline"], D2)
    assert not [
        item
        for item in (await client.get("/notifications", headers=other_student)).json()
        if item["type"] == "deadline_changed"
    ]

    await put_deadline(client, curator, g1, step, D1)
    mine = (await client.get("/notifications", headers=student)).json()
    changed = [item for item in mine if item["type"] == "deadline_changed"]
    assert changed[0]["payload"]["step_id"] == step
    assert same_time(changed[0]["payload"]["deadline"], D1)

    await client.delete(f"/groups/{g1}/deadlines/{step}", headers=curator)
    mine = (await client.get("/notifications", headers=student)).json()
    changed = [item for item in mine if item["type"] == "deadline_changed"]
    assert len(changed) == 3
    assert same_time(changed[0]["payload"]["deadline"], D2)

    await client.delete(url, headers=curator)
    mine = (await client.get("/notifications", headers=student)).json()
    changed = [item for item in mine if item["type"] == "deadline_changed"]
    assert len(changed) == 4
    assert changed[0]["payload"]["deadline"] is None
    assert same_time(changed[0]["payload"]["previous"], D2)


async def test_replace_and_delete(client, admin, course, groups_setup):
    (g1, curator, _, student), _ = groups_setup
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    await put_deadline(client, curator, g1, s1, D1)
    await put_deadline(client, curator, g1, s2, D2)

    r = await put_deadline(client, admin[1], g1, s1, D2)  # replace
    assert same_time(r.json()["due_at"], D2)
    rows = await listing(client, curator, g1, course[0])
    assert rows[0]["own"]["set_by"] != rows[1]["own"]["set_by"]  # admin vs curator

    assert (
        await client.delete(f"/groups/{g1}/deadlines/{s1}", headers=curator)
    ).status_code == 204
    # s1 now inherits s2's deadline instead of having its own.
    step = (await client.get(f"/steps/{s1}", headers=student)).json()
    assert step["deadline"]["inherited"] and step["deadline"]["source_step_id"] == s2
    assert (
        await client.delete(f"/groups/{g1}/deadlines/{s1}", headers=curator)
    ).status_code == 404


async def test_hidden_steps_are_skipped(client, admin, course, groups_setup):
    (g1, curator, _, _), _ = groups_setup
    s1 = await add_step(client, admin, course[1], single_choice())
    hidden = await add_step(client, admin, course[1], single_choice())
    await put_deadline(client, curator, g1, hidden)
    await client.patch(
        f"/admin/steps/{hidden}", json={"is_hidden": True}, headers=admin[1]
    )
    rows = await listing(client, curator, g1, course[0])
    assert [r["step_id"] for r in rows] == [s1]
    assert rows[0]["effective"] is None  # a hidden step's deadline does not spread


@pytest.mark.parametrize(
    ("due_at", "code"),
    [("2026-10-01T23:59:00", 422), ("not a date", 422)],
)
async def test_invalid_input(client, admin, course, groups_setup, due_at, code):
    (g1, curator, _, _), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    # Without a timezone the moment is ambiguous.
    assert (await put_deadline(client, curator, g1, step, due_at)).status_code == code


async def test_unknown_group_or_step(client, admin, course, groups_setup):
    (g1, curator, _, _), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    assert (await put_deadline(client, admin[1], 999, step)).status_code == 404
    assert (await put_deadline(client, curator, g1, 999)).status_code == 404
    await client.delete(f"/admin/steps/{step}", headers=admin[1])
    assert (await put_deadline(client, curator, g1, step)).status_code == 404


# --- "late" mark -----------------------------------------------------------

PAST = "2020-01-01T00:00:00+00:00"
FUTURE = "2099-01-01T00:00:00+00:00"


async def test_late_mark_for_student(client, admin, course, groups_setup):
    (g1, curator, _, student), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice(max_attempts=5))

    first = (await submit(client, student, step, {"option_id": B})).json()
    assert (first["is_late"], first["deadline_due_at"]) == (False, None)

    await put_deadline(client, curator, g1, step, PAST)
    late = (await submit(client, student, step, {"option_id": B})).json()
    assert late["is_late"] and same_time(late["deadline_due_at"], PAST)
    # A late submission is accepted and graded as usual: it is only a mark.
    assert late["status"] == "wrong"
    # The mark is computed against the current deadline, also for old ones.
    mine = (await client.get(f"/steps/{step}/submissions", headers=student)).json()
    assert [s["is_late"] for s in mine] == [True, True]

    # Extending the deadline clears the mark.
    await put_deadline(client, curator, g1, step, FUTURE)
    again = (await client.get(f"/submissions/{first['id']}", headers=student)).json()
    assert not again["is_late"] and same_time(again["deadline_due_at"], FUTURE)


async def test_inherited_deadline_marks_late(client, admin, course, groups_setup):
    (g1, curator, _, student), _ = groups_setup
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    await put_deadline(client, curator, g1, s2, PAST)
    r = (await submit(client, student, s1, {"option_id": A})).json()
    assert r["is_late"]


async def test_no_group_is_never_late(client, admin, course, make_user, groups_setup):
    (g1, curator, _, _), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    await put_deadline(client, curator, g1, step, PAST)
    _, loner = await make_user()
    r = (await submit(client, loner, step, {"option_id": A})).json()
    assert (r["is_late"], r["deadline_due_at"]) == (False, None)


async def test_curator_sees_late_mark(client, admin, course, groups_setup):
    (g1, curator, _, student), _ = groups_setup
    step = await add_step(client, admin, course[1], free_text())
    await put_deadline(client, curator, g1, step, PAST)
    sub_id = (await submit(client, student, step, {"text": "late essay"})).json()["id"]

    queue = (await client.get("/review/submissions", headers=curator)).json()
    assert queue[0]["is_late"] and same_time(queue[0]["deadline_due_at"], PAST)
    detail = (await client.get(f"/review/submissions/{sub_id}", headers=curator)).json()
    assert detail["is_late"]
    r = await client.post(
        f"/review/submissions/{sub_id}", json={"verdict": "accepted"}, headers=curator
    )
    assert r.json()["is_late"] and r.json()["status"] == "accepted"
