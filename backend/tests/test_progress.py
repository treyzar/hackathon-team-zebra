"""Course progress: totals, per-step breakdown, course changes, access."""

import pytest
from conftest import requires_db
from test_api import (
    DOC,
    A,
    B,
    add_step,
    free_text,
    multiple_choice,
    programming,
    single_choice,
    submit,
)

pytestmark = requires_db
THEORY = {"type": "theory", "content": {"body": DOC}}


async def progress(client, headers, course_id):
    r = await client.get(f"/courses/{course_id}/progress", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def by_step(p):
    return {s["step_id"]: s for s in p["steps"]}


@pytest.fixture
async def student(make_user):
    return (await make_user())[1]


async def test_totals_and_breakdown(client, admin, course, student):
    theory = await add_step(client, admin, course[1], THEORY)
    single = await add_step(client, admin, course[1], single_choice())  # max 2
    multi = await add_step(client, admin, course[1], multiple_choice())  # max 4
    essay = await add_step(client, admin, course[1], free_text())  # max 5

    await submit(client, student, theory, {})
    await submit(client, student, single, {"option_id": A})
    await submit(client, student, multi, {"option_ids": [A]})  # 2 of 4

    p = await progress(client, student, course[0])
    assert (p["steps_completed"], p["steps_passed"], p["steps_total"]) == (2, 2, 4)
    assert p["percent"] == 50
    # Partial points with attempts left: may still improve, not completed.
    assert not by_step(p)[multi]["completed"]
    assert (p["points_earned"], p["points_max"]) == (4, 11)
    assert p["next_step_id"] == essay  # the first step not tried yet
    steps = by_step(p)
    assert [steps[s]["state"] for s in (theory, single, multi, essay)] == [
        "passed",
        "passed",
        "partial",
        "not_started",
    ]
    # What each point came from.
    assert steps[multi] | {"best_submission_id": None} == steps[multi] | {
        "state": "partial",
        "earned": 2,
        "max_score": 4,
        "graded_by": "auto",
        "best_submission_id": None,
        "from_previous_version": False,
    }
    assert steps[multi]["best_submission_id"] is not None
    assert steps[theory]["max_score"] == 0

    # The same totals in the course list and the course tree.
    listed = (await client.get("/courses", headers=student)).json()[0]["progress"]
    tree = (await client.get(f"/courses/{course[0]}", headers=student)).json()
    summary = {
        k: v for k, v in p.items() if k not in ("steps", "modules", "course_id", "lag")
    }
    assert listed == summary == tree["progress"]


async def test_curator_grade_counts_like_auto(client, admin, course, groups_setup):
    (_, curator, _, student) = groups_setup[0]
    essay = await add_step(client, admin, course[1], free_text())

    sub = (await submit(client, student, essay, {"text": "v1"})).json()
    assert by_step(await progress(client, student, course[0]))[essay]["state"] == (
        "checking"
    )
    await client.post(
        f"/review/submissions/{sub['id']}",
        json={"verdict": "accepted", "score": 3},
        headers=curator,
    )
    step = by_step(await progress(client, student, course[0]))[essay]
    assert (step["state"], step["earned"], step["graded_by"]) == (
        "partial",
        3,
        "curator",
    )

    sub = (await submit(client, student, essay, {"text": "v2"})).json()
    await client.post(
        f"/review/submissions/{sub['id']}",
        json={"verdict": "accepted"},
        headers=curator,
    )
    p = await progress(client, student, course[0])
    assert (p["steps_passed"], p["points_earned"]) == (1, 5)


async def test_failed_and_attempts_exhausted(client, admin, course, student):
    step_id = await add_step(client, admin, course[1], single_choice(max_attempts=2))
    await submit(client, student, step_id, {"option_id": B})
    p = await progress(client, student, course[0])
    assert by_step(p)[step_id]["state"] == "failed"
    assert p["next_step_id"] == step_id  # may try again

    await submit(client, student, step_id, {"option_id": B})
    p = await progress(client, student, course[0])
    assert by_step(p)[step_id] | {"best_submission_id": None} == {
        "step_id": step_id,
        "module_id": course[1],
        "type": "single_choice",
        "state": "attempts_exhausted",
        "earned": 0,
        "max_score": 2,
        "graded_by": "auto",
        "best_submission_id": None,
        "from_previous_version": False,
        "attempts_used": 2,
        "max_attempts": 2,
        # No points and no attempts: not completed.
        "completed": False,
    }
    assert p["next_step_id"] is None  # nothing left to do


async def test_best_attempt_counts(client, admin, course, student):
    step_id = await add_step(client, admin, course[1], multiple_choice())
    first = await submit(client, student, step_id, {"option_ids": [A]})
    worse = await submit(client, student, step_id, {"option_ids": []})
    assert (first.json()["score"], worse.json()["score"]) == (2, 0)
    step = by_step(await progress(client, student, course[0]))[step_id]
    # The latest try was worse; the best one counts.
    assert (step["earned"], step["attempts_used"]) == (2, 2)
    assert step["best_submission_id"] == first.json()["id"]


async def test_course_changes_are_predictable(client, admin, course, student):
    s1 = await add_step(client, admin, course[1], single_choice())
    await submit(client, student, s1, {"option_id": A})
    before = await progress(client, student, course[0])
    assert (before["steps_passed"], before["steps_total"]) == (1, 1)

    # A new step shows up as not started and raises the totals.
    s2 = await add_step(client, admin, course[1], single_choice())
    p = await progress(client, student, course[0])
    assert (p["steps_passed"], p["steps_total"], p["percent"]) == (1, 2, 50)
    assert by_step(p)[s2]["state"] == "not_started" and p["next_step_id"] == s2

    # Reordering changes nothing but the order.
    await client.put(
        f"/admin/modules/{course[1]}/steps/order",
        json={"ids": [s2, s1]},
        headers=admin[1],
    )
    reordered = await progress(client, student, course[0])
    assert [s["step_id"] for s in reordered["steps"]] == [s2, s1]
    assert reordered["percent"] == 50

    # A hidden step drops out of the totals.
    await client.patch(f"/admin/steps/{s2}", json={"is_hidden": True}, headers=admin[1])
    assert (await progress(client, student, course[0]))["steps_total"] == 1

    # A deleted step too; its submissions stay in the history.
    await client.patch(
        f"/admin/steps/{s2}", json={"is_hidden": False}, headers=admin[1]
    )
    await client.delete(f"/admin/steps/{s1}", headers=admin[1])
    p = await progress(client, student, course[0])
    assert (p["steps_passed"], p["steps_total"]) == (0, 1)


async def test_breaking_change_keeps_result(client, admin, course, student):
    step_id = await add_step(client, admin, course[1], single_choice())  # max 2
    await submit(client, student, step_id, {"option_id": A})

    changed = single_choice()
    changed["answer_key"] = {"correct": B}
    changed["max_score"] = 4
    r = await client.post(
        f"/admin/steps/{step_id}/revisions",
        json={"payload": changed, "is_breaking": True},
        headers=admin[1],
    )
    assert r.status_code == 200

    step = by_step(await progress(client, student, course[0]))[step_id]
    # 2 of 2 before keeps its share: 4 of 4 now. Not lost, not replaced.
    assert (step["state"], step["earned"], step["max_score"]) == ("passed", 4, 4)
    assert step["from_previous_version"] and step["attempts_used"] == 0

    # The student may take the new version; a worse try changes nothing.
    view = (await client.get(f"/steps/{step_id}", headers=student)).json()
    assert view["can_submit"]
    await submit(client, student, step_id, {"option_id": A})  # wrong now
    step = by_step(await progress(client, student, course[0]))[step_id]
    assert (step["earned"], step["from_previous_version"]) == (4, True)
    assert step["attempts_used"] == 1


async def test_next_step_skips_locked_and_checking(client, admin, course, student):
    await client.patch(
        f"/admin/courses/{course[0]}",
        json={"step_access": "sequential"},
        headers=admin[1],
    )
    s1 = await add_step(client, admin, course[1], free_text())
    s2 = await add_step(client, admin, course[1], single_choice())
    await add_step(client, admin, course[1], single_choice())
    assert (await progress(client, student, course[0]))["next_step_id"] == s1

    await submit(client, student, s1, {"text": "essay"})  # waits for a curator
    # s1 is being checked; s2 is open now and is what to do next.
    assert (await progress(client, student, course[0]))["next_step_id"] == s2


async def test_group_progress_access(client, admin, course, groups_setup):
    (g1, curator1, student1_id, student1), (g2, _, _, _) = groups_setup
    step_id = await add_step(client, admin, course[1], single_choice())
    await submit(client, student1, step_id, {"option_id": A})

    url = f"/groups/{g1}/courses/{course[0]}/progress"
    rows = (await client.get(url, headers=curator1)).json()
    assert [(r["student_id"], r["progress"]["steps_passed"]) for r in rows] == [
        (student1_id, 1)
    ]
    other = f"/groups/{g2}/courses/{course[0]}/progress"
    assert (await client.get(other, headers=curator1)).status_code == 403
    assert (await client.get(url, headers=student1)).status_code == 403
    assert (await client.get(other, headers=admin[1])).status_code == 200


async def test_unpublished_course_has_no_progress(client, admin, course, student):
    await client.patch(
        f"/admin/courses/{course[0]}", json={"is_published": False}, headers=admin[1]
    )
    r = await client.get(f"/courses/{course[0]}/progress", headers=student)
    assert r.status_code == 404


async def test_nothing_next_while_tests_run(client, admin, course, student):
    await client.patch(
        f"/admin/courses/{course[0]}",
        json={"step_access": "sequential"},
        headers=admin[1],
    )
    code = await add_step(client, admin, course[1], programming())
    await add_step(client, admin, course[1], single_choice())
    await submit(client, student, code, {"code": "print(1)"})  # queued for tests

    p = await progress(client, student, course[0])
    assert by_step(p)[code]["state"] == "checking"
    # The next step opens only after the tests; until then there is nothing to
    # do, rather than pointing at a locked step.
    assert p["next_step_id"] is None


async def test_module_totals(client, admin, course, student):
    m1 = course[1]
    m2 = (
        await client.post(
            f"/admin/courses/{course[0]}/modules",
            json={"title": "Two"},
            headers=admin[1],
        )
    ).json()["id"]
    m3 = (
        await client.post(
            f"/admin/courses/{course[0]}/modules",
            json={"title": "Empty"},
            headers=admin[1],
        )
    ).json()["id"]
    a1 = await add_step(client, admin, m1, single_choice())  # max 2
    await add_step(client, admin, m1, single_choice())
    b1 = await add_step(client, admin, m2, multiple_choice())  # max 4
    hidden = await add_step(client, admin, m2, single_choice())
    await client.patch(
        f"/admin/steps/{hidden}", json={"is_hidden": True}, headers=admin[1]
    )

    await submit(client, student, a1, {"option_id": A})
    await submit(client, student, b1, {"option_ids": [A]})  # 2 of 4

    p = await progress(client, student, course[0])
    totals = {
        m["module_id"]: (
            m["title"],
            m["steps_passed"],
            m["steps_total"],
            m["points_earned"],
            m["points_max"],
            m["percent"],
        )
        for m in p["modules"]
    }
    assert [m["module_id"] for m in p["modules"]] == [m1, m2, m3]
    assert totals[m1] == ("Intro", 1, 2, 2, 4, 50)
    assert totals[m2] == ("Two", 0, 1, 2, 4, 0)  # the hidden step does not count
    assert totals[m3] == ("Empty", 0, 0, 0, 0, 0)
    # The course is the sum of its modules.
    assert p["steps_total"] == sum(m["steps_total"] for m in p["modules"])
    assert p["points_earned"] == sum(m["points_earned"] for m in p["modules"])

    # The course tree shows the same per module.
    tree = (await client.get(f"/courses/{course[0]}", headers=student)).json()
    tree_totals = {m["id"]: m["progress"] for m in tree["modules"]}
    for m in p["modules"]:
        expected = {k: v for k, v in m.items() if k not in ("module_id", "title")}
        assert tree_totals[m["module_id"]] == expected


async def test_partial_without_attempts_is_completed(client, admin, course, student):
    s1 = await add_step(client, admin, course[1], multiple_choice(max_attempts=1))
    s2 = await add_step(client, admin, course[1], single_choice())
    await submit(client, student, s1, {"option_ids": [A]})  # 2 of 4, no tries left

    p = await progress(client, student, course[0])
    step = by_step(p)[s1]
    assert (step["state"], step["earned"], step["completed"]) == ("partial", 2, True)
    # Counts towards the percent, but not as reached the maximum.
    assert (p["steps_completed"], p["steps_passed"], p["percent"]) == (1, 0, 50)
    assert p["next_step_id"] == s2  # nothing more to do on s1


async def test_curator_acceptance_completes_step(client, admin, course, groups_setup):
    (_, curator, _, student) = groups_setup[0]
    essay = await add_step(client, admin, course[1], free_text())  # max 5
    later = await add_step(client, admin, course[1], single_choice())

    sub = (await submit(client, student, essay, {"text": "v1"})).json()
    await client.post(
        f"/review/submissions/{sub['id']}",
        json={"verdict": "rejected", "comment": "redo"},
        headers=curator,
    )
    step = by_step(await progress(client, student, course[0]))[essay]
    assert (step["state"], step["completed"]) == ("failed", False)

    sub = (await submit(client, student, essay, {"text": "v2"})).json()
    await client.post(
        f"/review/submissions/{sub['id']}",
        json={"verdict": "accepted", "score": 3},
        headers=curator,
    )
    p = await progress(client, student, course[0])
    step = by_step(p)[essay]
    # Accepted with 3 of 5 and unlimited attempts: completed all the same.
    assert (step["state"], step["earned"], step["completed"]) == ("partial", 3, True)
    assert p["steps_completed"] == 1
    # Forward first: the untouched step comes before improving the essay.
    assert p["next_step_id"] == later
    await submit(client, student, later, {"option_id": A})
    p = await progress(client, student, course[0])
    assert p["next_step_id"] == essay  # now it is worth improving
