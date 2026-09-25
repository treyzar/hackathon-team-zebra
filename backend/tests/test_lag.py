"""Falling behind schedule: on_track / slowed / falling_behind and reasons."""

from datetime import UTC, datetime, timedelta

import pytest
from conftest import requires_db
from test_api import A, B, add_step, free_text, multiple_choice, single_choice, submit
from test_rating import join

pytestmark = requires_db


def days_ago(days: float) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


async def deadline(client, headers, group_id, step_id, due_at):
    r = await client.put(
        f"/groups/{group_id}/deadlines/{step_id}",
        json={"due_at": due_at},
        headers=headers,
    )
    assert r.status_code == 200, r.text


async def lag(client, headers, course_id):
    r = await client.get(f"/courses/{course_id}/progress", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["lag"]


@pytest.fixture
def g1(groups_setup):
    group_id, curator, _, student = groups_setup[0]
    return group_id, curator, student


async def test_on_track(client, admin, course, g1):
    group_id, curator, student = g1
    step = await add_step(client, admin, course[1], single_choice())
    assert await lag(client, student, course[0]) == {
        "status": "on_track",
        "overdue": [],
    }
    await deadline(client, curator, group_id, step, days_ago(-3))  # in 3 days
    assert (await lag(client, student, course[0]))["status"] == "on_track"


async def test_slowed_within_a_week(client, admin, course, g1):
    group_id, curator, student = g1
    step = await add_step(client, admin, course[1], single_choice())
    await deadline(client, curator, group_id, step, days_ago(3))
    got = await lag(client, student, course[0])
    assert got["status"] == "slowed"
    assert [
        (o["step_id"], o["days_overdue"], o["state"], o["module_title"], o["position"])
        for o in got["overdue"]
    ] == [(step, 3, "not_started", "Intro", 1)]


@pytest.mark.parametrize(("days", "status"), [(6.9, "slowed"), (7.1, "falling_behind")])
async def test_one_week_boundary(client, admin, course, g1, days, status):
    group_id, curator, student = g1
    step = await add_step(client, admin, course[1], single_choice())
    await deadline(client, curator, group_id, step, days_ago(days))
    assert (await lag(client, student, course[0]))["status"] == status


async def test_falling_behind_lists_most_overdue_first(client, admin, course, g1):
    group_id, curator, student = g1
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    await deadline(client, curator, group_id, s1, days_ago(10))
    await deadline(client, curator, group_id, s2, days_ago(2))
    got = await lag(client, student, course[0])
    assert got["status"] == "falling_behind"
    assert [(o["step_id"], o["days_overdue"]) for o in got["overdue"]] == [
        (s1, 10),
        (s2, 2),
    ]


async def test_late_completion_clears_and_is_not_blocked(client, admin, course, g1):
    group_id, curator, student = g1
    step = await add_step(client, admin, course[1], single_choice())
    await deadline(client, curator, group_id, step, days_ago(10))
    assert (await lag(client, student, course[0]))["status"] == "falling_behind"

    # The deadline is information only: a late submission is accepted.
    r = await submit(client, student, step, {"option_id": A})
    assert r.status_code == 201 and r.json()["is_late"]
    assert (await lag(client, student, course[0]))["status"] == "on_track"


async def test_waiting_for_check_is_not_overdue(client, admin, course, g1):
    group_id, curator, student = g1
    essay = await add_step(client, admin, course[1], free_text())
    await deadline(client, curator, group_id, essay, days_ago(3))
    await submit(client, student, essay, {"text": "late essay"})
    assert (await lag(client, student, course[0]))["status"] == "on_track"


async def test_stuck_steps_stay_overdue_with_reason(client, admin, course, g1):
    group_id, curator, student = g1
    exhausted = await add_step(client, admin, course[1], single_choice(max_attempts=1))
    failed = await add_step(client, admin, course[1], single_choice())
    partial = await add_step(client, admin, course[1], multiple_choice())
    for step in (exhausted, failed, partial):
        await deadline(client, curator, group_id, step, days_ago(2))
    await submit(client, student, exhausted, {"option_id": B})  # 0, no tries
    await submit(client, student, failed, {"option_id": B})  # 0, may retry
    await submit(client, student, partial, {"option_ids": [A]})  # 2 of 4

    reasons = {
        o["step_id"]: o["state"]
        for o in (await lag(client, student, course[0]))["overdue"]
    }
    assert reasons == {
        exhausted: "attempts_exhausted",
        failed: "failed",
        partial: "partial",
    }


async def test_inherited_deadline_counts(client, admin, course, g1):
    group_id, curator, student = g1
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    await deadline(client, curator, group_id, s2, days_ago(3))
    overdue = (await lag(client, student, course[0]))["overdue"]
    assert {o["step_id"] for o in overdue} == {s1, s2}


async def test_no_group_is_on_track(client, admin, course, make_user, g1):
    group_id, curator, _ = g1
    step = await add_step(client, admin, course[1], single_choice())
    await deadline(client, curator, group_id, step, days_ago(10))
    _, loner = await make_user()
    assert (await lag(client, loner, course[0]))["status"] == "on_track"


async def test_curator_finds_lagging_students(
    client, admin, course, make_user, groups_setup
):
    (group_id, curator, slow_id, slow), (_, other_curator, _, _) = groups_setup
    s1 = await add_step(client, admin, course[1], single_choice())
    s2 = await add_step(client, admin, course[1], single_choice())
    await deadline(client, curator, group_id, s1, days_ago(10))
    await deadline(client, curator, group_id, s2, days_ago(2))
    behind_id, _ = await join(client, admin, make_user, group_id)  # nothing done
    ok_id, ok = await join(client, admin, make_user, group_id)
    await submit(client, slow, s1, {"option_id": A})  # only s2 overdue now
    await submit(client, ok, s1, {"option_id": A})
    await submit(client, ok, s2, {"option_id": A})

    url = f"/groups/{group_id}/courses/{course[0]}/lagging"
    rows = (await client.get(url, headers=curator)).json()
    # Worst first; students on track are not listed.
    assert [(r["student_id"], r["lag"]["status"]) for r in rows] == [
        (behind_id, "falling_behind"),
        (slow_id, "slowed"),
    ]
    assert [o["step_id"] for o in rows[0]["lag"]["overdue"]] == [s1, s2]
    assert all(r["username"] for r in rows)

    # The same status is in the group progress table.
    table = (
        await client.get(
            f"/groups/{group_id}/courses/{course[0]}/progress", headers=curator
        )
    ).json()
    assert {r["student_id"]: r["lag"]["status"] for r in table} == {
        behind_id: "falling_behind",
        slow_id: "slowed",
        ok_id: "on_track",
    }

    assert (await client.get(url, headers=other_curator)).status_code == 403
    assert (await client.get(url, headers=slow)).status_code == 403
    assert (await client.get(url, headers=admin[1])).status_code == 200
