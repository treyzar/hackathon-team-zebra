"""Analytics of a course for one group: modules, students, step results."""

import pytest
from conftest import requires_db
from test_api import DOC, A, B, add_step, free_text, single_choice, submit
from test_deadlines import PAST, put_deadline

pytestmark = requires_db

THEORY = {"type": "theory", "content": {"body": DOC}}
TITLED = {
    "type": "doc",
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 1, "zebra_title": True},
            "content": [{"type": "text", "text": "Чётность"}],
        }
    ],
}


async def join_group(client, admin, make_user, group_id, enroll=True):
    student_id, headers = await make_user(enroll=enroll)
    r = await client.put(
        f"/admin/groups/{group_id}/students/{student_id}", headers=admin[1]
    )
    assert r.status_code == 204
    return student_id, headers


async def review(client, curator, sub_id, verdict):
    r = await client.post(
        f"/review/submissions/{sub_id}", json={"verdict": verdict}, headers=curator
    )
    assert r.status_code == 200, r.text


@pytest.fixture
async def scene(client, admin, course, groups_setup, make_user):
    """Module 1: theory, choice, free text; module 2: one choice step.

    s1 — in progress: choice on the 2nd attempt, free text rejected (not
    resubmitted); s2 — passed module 1: choice on the 1st attempt, free text
    rejected, resubmitted and accepted; s3 — did nothing. Plus a student of
    another group and a group member not enrolled in the course."""
    (g1, curator, s1_id, s1), (_, _, _, other) = groups_setup
    s2_id, s2 = await join_group(client, admin, make_user, g1)
    s3_id, _ = await join_group(client, admin, make_user, g1)
    await join_group(client, admin, make_user, g1, enroll=False)

    choice = single_choice()
    choice["content"]["question"] = TITLED
    theory = await add_step(client, admin, course[1], THEORY)
    task = await add_step(client, admin, course[1], choice)
    essay = await add_step(client, admin, course[1], free_text())
    module2 = (
        await client.post(
            f"/admin/courses/{course[0]}/modules",
            json={"title": "Второй"},
            headers=admin[1],
        )
    ).json()["id"]
    await add_step(client, admin, module2, single_choice())
    await put_deadline(client, curator, g1, essay, PAST)

    await submit(client, s1, theory, {})
    await submit(client, s1, task, {"option_id": B})
    await submit(client, s1, task, {"option_id": A})
    sub = (await submit(client, s1, essay, {"text": "1"})).json()["id"]
    await review(client, curator, sub, "rejected")

    await submit(client, s2, theory, {})
    await submit(client, s2, task, {"option_id": A})
    sub = (await submit(client, s2, essay, {"text": "1"})).json()["id"]
    await review(client, curator, sub, "rejected")
    sub = (await submit(client, s2, essay, {"text": "2"})).json()["id"]
    await review(client, curator, sub, "accepted")

    # Other groups do not count.
    await submit(client, other, task, {"option_id": B})
    return {
        "g1": g1,
        "curator": curator,
        "ids": (s1_id, s2_id, s3_id),
        "steps": (theory, task, essay),
        "modules": (course[1], module2),
    }


async def get(client, headers, url):
    r = await client.get(url, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_course_analytics(client, course, scene):
    s1, s2, s3 = scene["ids"]
    m1, m2 = scene["modules"]
    data = await get(
        client, scene["curator"], f"/groups/{scene['g1']}/courses/{course[0]}/analytics"
    )
    assert data["students_total"] == 3
    first, second = data["modules"]
    assert first["module_id"] == m1
    assert (
        first["students_passed"],
        first["students_in_progress"],
        first["students_not_started"],
    ) == (1, 1, 1)
    # First attempts at tasks: s1 choice wrong, s2 choice right, both essays
    # rejected -> 1 of 4. Attempts: 2 + 1 + 1 + 2 over 4 pairs. Two returns.
    assert (first["first_attempt_percent"], first["avg_attempts"]) == (25, 1.5)
    assert first["returns"] == 2
    assert (second["module_id"], second["students_not_started"]) == (m2, 3)
    assert (second["first_attempt_percent"], second["avg_attempts"]) == (None, None)

    rows = {r["student_id"]: r for r in data["students"]}
    assert set(rows) == {s1, s2, s3}
    one, two, three = rows[s1], rows[s2], rows[s3]
    assert [
        (
            m["state"],
            m["steps_completed"],
            m["steps_total"],
            m["has_submissions"],
            m["has_unresolved_return"],
        )
        for m in one["modules"]
    ] == [("in_progress", 2, 3, True, True), ("not_started", 0, 1, False, False)]
    assert [(m["state"], m["has_unresolved_return"]) for m in two["modules"]] == [
        ("passed", False),
        ("not_started", False),
    ]
    # The essay is overdue for s1; s3 inherits the deadline on earlier steps.
    assert (one["lag"]["status"], two["lag"]["status"]) == (
        "falling_behind",
        "on_track",
    )
    assert three["lag"]["status"] == "falling_behind"
    assert one["last_submission_at"] and two["last_submission_at"]
    assert three["last_submission_at"] is None
    assert (one["name"], one["surname"]) == ("Имя", one["username"].capitalize())


async def test_module_analytics(client, course, scene):
    s1, s2, s3 = scene["ids"]
    theory, task, essay = scene["steps"]
    m1 = scene["modules"][0]
    data = await get(
        client,
        scene["curator"],
        f"/groups/{scene['g1']}/courses/{course[0]}/modules/{m1}/analytics",
    )
    assert [(c["step_id"], c["position"], c["type"]) for c in data["steps"]] == [
        (theory, 1, "theory"),
        (task, 2, "single_choice"),
        (essay, 3, "free_text"),
    ]
    assert data["steps"][1]["title"] == "Чётность"
    assert data["module"]["returns"] == 2

    rows = {
        r["student_id"]: {c["step_id"]: c for c in r["steps"]} for r in data["students"]
    }
    assert set(rows) == {s1, s2, s3}
    cell = rows[s1]
    assert (cell[task]["state"], cell[task]["attempts"]) == ("passed", 2)
    assert cell[task]["first_attempt_solved"] is False
    assert cell[theory]["first_attempt_solved"] is None
    assert (cell[essay]["state"], cell[essay]["has_unresolved_return"]) == (
        "failed",
        True,
    )
    assert (rows[s2][essay]["completed"], rows[s2][essay]["attempts"]) == (True, 2)
    assert rows[s2][essay]["has_unresolved_return"] is False
    assert rows[s2][task]["first_attempt_solved"] is True
    assert all(
        c["state"] == "not_started" and c["attempts"] == 0 for c in rows[s3].values()
    )


async def test_analytics_access(client, admin, course, scene, groups_setup, make_user):
    (_, _, _, student), (g2, curator2, _, _) = groups_setup
    base = f"/groups/{scene['g1']}/courses/{course[0]}"
    m1 = scene["modules"][0]
    for url in (f"{base}/analytics", f"{base}/modules/{m1}/analytics"):
        assert (await client.get(url, headers=curator2)).status_code == 403
        assert (await client.get(url, headers=student)).status_code == 403
        assert (await client.get(url, headers=admin[1])).status_code == 200
    r = await client.get(f"{base}/modules/999999/analytics", headers=admin[1])
    assert r.status_code == 404
    # A module of another course is not found in this one.
    other = (
        await client.post(
            "/admin/courses", json={"slug": "x", "title": "X"}, headers=admin[1]
        )
    ).json()["id"]
    foreign = (
        await client.post(
            f"/admin/courses/{other}/modules", json={"title": "M"}, headers=admin[1]
        )
    ).json()["id"]
    r = await client.get(f"{base}/modules/{foreign}/analytics", headers=admin[1])
    assert r.status_code == 404


async def test_judge_failure_is_not_an_attempt(client, admin, course, groups_setup):
    from sqlalchemy import update

    from database import async_factory
    from submissions.models import Submission, SubmissionStatus

    (g1, curator, _, student), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    sub = (await submit(client, student, step, {"option_id": B})).json()["id"]
    async with async_factory() as db, db.begin():
        await db.execute(
            update(Submission)
            .where(Submission.id == sub)
            .values(status=SubmissionStatus.ERROR, score=None)
        )

    data = await get(client, curator, f"/groups/{g1}/courses/{course[0]}/analytics")
    [module] = data["modules"]
    assert (module["students_not_started"], module["avg_attempts"]) == (1, None)
    assert data["students"][0]["last_submission_at"] is None
