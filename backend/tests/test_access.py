"""Course setting step_access: all steps open vs. sequential unlocking."""

import pytest
from conftest import LocalJudge, requires_db
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
from test_worker import drain

pytestmark = requires_db
THEORY = {"type": "theory", "content": {"body": DOC}}


async def make_sequential(client, admin, course):
    r = await client.patch(
        f"/admin/courses/{course[0]}",
        json={"step_access": "sequential"},
        headers=admin[1],
    )
    assert r.json()["step_access"] == "sequential"


async def locks(client, headers, course_id):
    """Locked flags of all steps in course order."""
    tree = (await client.get(f"/courses/{course_id}", headers=headers)).json()
    return [s["locked"] for m in tree["modules"] for s in m["steps"]]


async def opens(client, headers, step_id) -> bool:
    r = await client.get(f"/steps/{step_id}", headers=headers)
    assert r.status_code in (200, 403), r.text
    return r.status_code == 200


@pytest.fixture
async def student(make_user):
    return (await make_user())[1]


async def test_all_steps_open_by_default(client, admin, course, student):
    ids = [await add_step(client, admin, course[1], single_choice()) for _ in range(3)]
    tree = (await client.get(f"/courses/{course[0]}", headers=student)).json()
    assert tree["step_access"] == "all"
    assert await locks(client, student, course[0]) == [False, False, False]
    assert await opens(client, student, ids[2])


async def test_create_course_with_setting(client, admin):
    r = await client.post(
        "/admin/courses",
        json={"slug": "seq", "title": "Seq", "step_access": "sequential"},
        headers=admin[1],
    )
    assert r.json()["step_access"] == "sequential"
    tree = await client.get(f"/admin/courses/{r.json()['id']}", headers=admin[1])
    assert tree.json()["step_access"] == "sequential"


async def test_locked_step_is_closed_everywhere(client, admin, course, student):
    await make_sequential(client, admin, course)
    s1, s2, s3 = [
        await add_step(client, admin, course[1], single_choice()) for _ in range(3)
    ]
    assert await locks(client, student, course[0]) == [False, True, True]

    # Every student endpoint of a locked step refuses.
    for r in (
        await client.get(f"/steps/{s2}", headers=student),
        await client.get(f"/steps/{s2}/answer", headers=student),
        await client.get(f"/steps/{s2}/submissions", headers=student),
        await submit(client, student, s2, {"option_id": A}),
    ):
        assert r.status_code == 403 and "locked" in r.json()["detail"]

    # A wrong answer with attempts left does not open the next step.
    await submit(client, student, s1, {"option_id": B})
    assert await locks(client, student, course[0]) == [False, True, True]
    await submit(client, student, s1, {"option_id": A})
    assert await locks(client, student, course[0]) == [False, False, True]
    assert await opens(client, student, s2)
    assert not await opens(client, student, s3)


async def test_partial_score_opens_next(client, admin, course, student):
    await make_sequential(client, admin, course)
    s1 = await add_step(client, admin, course[1], multiple_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    assert not await opens(client, student, s2)
    r = await submit(client, student, s1, {"option_ids": [A]})
    assert (r.json()["status"], r.json()["score"]) == ("partial", 2)
    assert await opens(client, student, s2)


async def test_used_up_attempts_open_next(client, admin, course, student):
    await make_sequential(client, admin, course)
    s1 = await add_step(client, admin, course[1], single_choice(max_attempts=1))
    s2 = await add_step(client, admin, course[1], single_choice())
    assert not await opens(client, student, s2)
    await submit(client, student, s1, {"option_id": B})  # wrong, no attempts left
    assert await opens(client, student, s2)


async def test_sent_to_curator_opens_next(client, admin, course, student):
    await make_sequential(client, admin, course)
    s1 = await add_step(client, admin, course[1], free_text())
    s2 = await add_step(client, admin, course[1], single_choice())
    assert not await opens(client, student, s2)
    r = await submit(client, student, s1, {"text": "essay"})
    assert r.json()["status"] == "pending_review"  # not reviewed yet
    assert await opens(client, student, s2)


async def test_theory_opens_next_once_viewed(client, admin, course, student):
    await make_sequential(client, admin, course)
    s1 = await add_step(client, admin, course[1], THEORY)
    s2 = await add_step(client, admin, course[1], single_choice())
    assert await opens(client, student, s1)
    assert not await opens(client, student, s2)
    await submit(client, student, s1, {})
    assert await opens(client, student, s2)


async def test_code_opens_next_after_check(client, admin, course, student):
    await make_sequential(client, admin, course)
    s1 = await add_step(client, admin, course[1], programming())
    s2 = await add_step(client, admin, course[1], single_choice())

    await submit(client, student, s1, {"code": "print(0)"})
    assert not await opens(client, student, s2)  # queued: not checked yet
    await drain(LocalJudge())
    assert not await opens(client, student, s2)  # checked: 0 points

    await submit(client, student, s1, {"code": "print(int(input()) ** 2)"})
    await drain(LocalJudge())
    assert await opens(client, student, s2)


async def test_tests_and_review_opens_when_sent_to_curator(
    client, admin, course, student
):
    await make_sequential(client, admin, course)
    s1 = await add_step(
        client, admin, course[1], programming(grading="tests_and_review")
    )
    s2 = await add_step(client, admin, course[1], single_choice())
    await submit(client, student, s1, {"code": "print(0)"})
    assert not await opens(client, student, s2)
    await drain(LocalJudge())  # tests done, now waits for the curator
    assert await opens(client, student, s2)


async def test_order_spans_modules_and_skips_hidden(client, admin, course, student):
    await make_sequential(client, admin, course)
    m2 = await client.post(
        f"/admin/courses/{course[0]}/modules", json={"title": "Two"}, headers=admin[1]
    )
    hidden = await add_step(client, admin, course[1], single_choice())
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, m2.json()["id"], single_choice())
    await client.patch(
        f"/admin/steps/{hidden}", json={"is_hidden": True}, headers=admin[1]
    )

    # The hidden step is skipped: s1 is the first step, so it is open.
    assert await locks(client, student, course[0]) == [False, True]
    await submit(client, student, s1, {"option_id": A})
    # The first step of the next module follows the last one of this module.
    assert await opens(client, student, s2)


async def test_started_step_stays_open(client, admin, course, student):
    await make_sequential(client, admin, course)
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    await submit(client, student, s1, {"option_id": A})
    await submit(client, student, s2, {"option_id": B})

    # A new step is inserted between them.
    new = await add_step(client, admin, course[1], single_choice())
    await client.put(
        f"/admin/modules/{course[1]}/steps/order",
        json={"ids": [s1, new, s2]},
        headers=admin[1],
    )
    assert await opens(client, student, new)  # s1 is passed
    assert await opens(client, student, s2)  # own work stays reachable


async def test_breaking_change_does_not_relock(client, admin, course, student):
    await make_sequential(client, admin, course)
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    await submit(client, student, s1, {"option_id": A})

    changed = single_choice()
    changed["answer_key"] = {"correct": B}
    r = await client.post(
        f"/admin/steps/{s1}/revisions",
        json={"payload": changed, "is_breaking": True},
        headers=admin[1],
    )
    assert r.status_code == 200
    assert await opens(client, student, s2)


@pytest.mark.parametrize("role", ["curator", "admin"])
async def test_staff_see_all_steps(client, admin, course, make_user, role):
    await make_sequential(client, admin, course)
    ids = [await add_step(client, admin, course[1], single_choice()) for _ in range(2)]
    _, h = await make_user(role)
    assert await locks(client, h, course[0]) == [False, False]
    assert await opens(client, h, ids[1])
