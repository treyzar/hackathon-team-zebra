"""Overall rating within a group: courses, streak bonus, places, targets."""

from datetime import UTC, datetime, timedelta

import pytest
from conftest import requires_db
from test_api import (
    DOC,
    A,
    B,
    add_step,
    free_text,
    multiple_choice,
    single_choice,
    submit,
)

pytestmark = requires_db
THEORY = {"type": "theory", "content": {"body": DOC}}


async def rating(client, headers):
    r = await client.get("/rating", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def join(client, admin, make_user, group_id, **kwargs):
    user_id, headers = await make_user(**kwargs)
    r = await client.put(
        f"/admin/groups/{group_id}/students/{user_id}", headers=admin[1]
    )
    assert r.status_code == 204
    return user_id, headers


async def set_sent_at(sub_id, when):
    from sqlalchemy import update

    from database import async_factory
    from submissions.models import Submission

    async with async_factory() as db, db.begin():
        await db.execute(
            update(Submission).where(Submission.id == sub_id).values(created_at=when)
        )


@pytest.fixture
async def ranked(client, admin, course, make_user, groups_setup):
    """Group of four with course points 6, 4, 4, 0 on steps A (2), B (4),
    C (2). Everyone with points sent them today: a 1-day streak, +2."""
    (g1, curator, s1_id, s1), _ = groups_setup
    await add_step(client, admin, course[1], THEORY)  # no points: never an option
    a = await add_step(client, admin, course[1], single_choice())
    b = await add_step(client, admin, course[1], multiple_choice())
    c = await add_step(client, admin, course[1], single_choice())
    s2_id, s2 = await join(client, admin, make_user, g1)
    s3_id, s3 = await join(client, admin, make_user, g1)
    s4_id, s4 = await join(client, admin, make_user, g1)

    await submit(client, s1, a, {"option_id": A})  # 2
    await submit(client, s1, b, {"option_ids": [A, B]})  # 4 -> 6
    await submit(client, s2, b, {"option_ids": [A, B]})  # 4
    await submit(client, s3, a, {"option_id": A})  # 2
    await submit(client, s3, b, {"option_ids": [A]})  # 2 of 4 -> 4
    return {
        "group": g1,
        "curator": curator,
        "steps": (a, b, c),
        "students": [(s1_id, s1), (s2_id, s2), (s3_id, s3), (s4_id, s4)],
    }


async def test_total_is_courses_plus_streak(client, course, ranked):
    got = [await rating(client, h) for _, h in ranked["students"]]
    assert [(r["total"], r["streak"]["bonus"]) for r in got] == [
        (8, 2),
        (6, 2),
        (6, 2),
        (0, 0),
    ]
    assert got[0]["courses"] == [
        {"course_id": course[0], "title": "Python", "points": 6}
    ]
    assert got[0]["streak"] == {"days": 1, "bonus": 2, "active_today": True}


async def test_places_share_on_ties(client, ranked):
    got = [await rating(client, h) for _, h in ranked["students"]]
    assert [(r["place"], r["tied_with"]) for r in got] == [
        (1, 0),
        (2, 1),
        (2, 1),
        (4, 0),
    ]
    assert all(r["group_size"] == 4 for r in got)


async def test_first_place_sees_no_targets_above(client, ranked):
    me = await rating(client, ranked["students"][0][1])
    assert me["next_place"] is None
    assert me["first_place"] == {
        "place": 1,
        "points": 8,
        "gap": None,
        "plan": [],
        "reachable": True,
    }


async def test_targets_skip_equal_ratings(client, ranked):
    a, b, c = ranked["steps"]
    me = await rating(client, ranked["students"][1][1])  # 6, tied
    # The tie at 6 is skipped: the next place above is the 8 at place 1.
    assert me["next_place"] | {"plan": None} == {
        "place": 1,
        "points": 8,
        "gap": 2,
        "plan": None,
        "reachable": True,
    }
    # 2 more only ties; A (2) + C (2) = 4 > 2 overtakes.
    assert me["next_place"]["plan"] == [a, c]


async def test_plan_completes_first_then_improves(client, course, ranked):
    a, b, c = ranked["steps"]
    me = await rating(client, ranked["students"][2][1])  # A 2, B 2/4
    assert [
        (o["step_id"], o["action"], o["can_gain"]) for o in me["opportunities"]
    ] == [
        (c, "complete", 2),
        (b, "improve", 2),
    ]
    assert me["next_place"]["gap"] == 2 and me["next_place"]["plan"] == [c, b]
    # Where each step is, as the student sees the course.
    first = me["opportunities"][0]
    assert (first["course_id"], first["course_title"]) == (course[0], "Python")
    assert (first["module_title"], first["position"]) == ("Intro", 4)


async def test_last_place_targets(client, ranked):
    a, b, c = ranked["steps"]
    me = await rating(client, ranked["students"][3][1])  # 0
    assert (me["next_place"]["place"], me["next_place"]["gap"]) == (2, 6)
    assert me["next_place"]["plan"] == [a, b, c]  # 2 + 4 = 6 ties, 8 > 6
    # All 8 points of the course only tie with the leader's 8.
    assert (me["first_place"]["gap"], me["first_place"]["reachable"]) == (8, False)
    assert me["first_place"]["plan"] == []


async def test_student_sees_no_one_else(client, ranked):
    leader = ranked["students"][0][1]
    leader_name = (await client.get("/user/me", headers=leader)).json()["username"]
    me = await rating(client, ranked["students"][3][1])
    # Only aggregates about others: no names, no ids of other students.
    assert leader_name not in str(me)
    assert set(me) == {
        "total",
        "courses",
        "streak",
        "group_size",
        "place",
        "tied_with",
        "next_place",
        "first_place",
        "opportunities",
    }
    assert set(me["first_place"]) == {"place", "points", "gap", "plan", "reachable"}


async def test_points_of_every_course(client, admin, course, groups_setup, make_user):
    (g1, curator, s1_id, s1), _ = groups_setup
    py_step = await add_step(client, admin, course[1], single_choice())
    algo = (
        await client.post(
            "/admin/courses",
            json={"slug": "algo", "title": "Алгоритмы"},
            headers=admin[1],
        )
    ).json()["id"]
    module = (
        await client.post(
            f"/admin/courses/{algo}/modules", json={"title": "M"}, headers=admin[1]
        )
    ).json()["id"]
    algo_step = await add_step(client, admin, module, multiple_choice())
    await client.patch(
        f"/admin/courses/{algo}", json={"is_published": True}, headers=admin[1]
    )
    await client.post(
        f"/admin/courses/{algo}/enrollments",
        json={"user_ids": [s1_id]},
        headers=admin[1],
    )
    # A groupmate studies only the first course.
    mate_id, mate = await join(client, admin, make_user, g1, enroll=False)
    await client.post(
        f"/admin/courses/{course[0]}/enrollments",
        json={"user_ids": [mate_id]},
        headers=admin[1],
    )

    await submit(client, s1, py_step, {"option_id": A})  # 2
    await submit(client, s1, algo_step, {"option_ids": [A, B]})  # 4
    await submit(client, mate, py_step, {"option_id": A})  # 2

    me = await rating(client, s1)
    assert me["courses"] == [
        {"course_id": course[0], "title": "Python", "points": 2},
        {"course_id": algo, "title": "Алгоритмы", "points": 4},
    ]
    assert me["total"] == 2 + 4 + 2
    theirs = await rating(client, mate)
    assert [c["course_id"] for c in theirs["courses"]] == [course[0]]
    assert (theirs["total"], theirs["place"], theirs["next_place"]["gap"]) == (4, 2, 4)
    # Opportunities come from the student's own courses only.
    assert {o["course_id"] for o in theirs["opportunities"]} <= {course[0]}

    rows = (await client.get(f"/groups/{g1}/rating", headers=curator)).json()
    assert [(r["place"], r["student_id"], r["total"]) for r in rows] == [
        (1, s1_id, 8),
        (2, mate_id, 4),
    ]
    assert rows[0]["courses"][1] == {
        "course_id": algo,
        "title": "Алгоритмы",
        "points": 4,
    }
    assert rows[0]["streak"]["bonus"] == 2 and rows[0]["name"] == "Имя"

    # An unpublished course does not count, even when enrolled.
    await client.patch(
        f"/admin/courses/{algo}", json={"is_published": False}, headers=admin[1]
    )
    assert (await rating(client, s1))["total"] == 2 + 2


async def test_streak_days(client, admin, course, groups_setup):
    (_, _, _, student), _ = groups_setup
    # A full score closes a step, so every submission gets its own.
    steps = [
        await add_step(client, admin, course[1], single_choice()) for _ in range(3)
    ]
    essay = await add_step(client, admin, course[1], free_text())
    day = timedelta(days=1)
    now = datetime.now(UTC)

    async def sent(step_id, answer, when):
        r = await submit(client, student, step_id, answer)
        assert r.status_code == 201, r.text
        await set_sent_at(r.json()["id"], when)

    # Two days ago and yesterday: points; today nothing yet.
    await sent(steps[0], {"option_id": A}, now - 2 * day)
    await sent(steps[1], {"option_id": A}, now - day)
    streak = (await rating(client, student))["streak"]
    # Kept from yesterday: the day is not over.
    assert streak == {"days": 2, "bonus": 4, "active_today": False}

    # Today: a wrong answer (0 points) does not count, work waiting for a
    # curator does.
    await sent(steps[2], {"option_id": B}, now)
    assert (await rating(client, student))["streak"]["active_today"] is False
    await sent(essay, {"text": "эссе"}, now)
    assert (await rating(client, student))["streak"] == {
        "days": 3,
        "bonus": 6,
        "active_today": True,
    }


async def test_missed_day_resets_streak(client, admin, course, groups_setup):
    (_, _, _, student), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    sub = (await submit(client, student, step, {"option_id": A})).json()["id"]
    await set_sent_at(sub, datetime.now(UTC) - timedelta(days=2))
    me = await rating(client, student)
    assert me["streak"] == {"days": 0, "bonus": 0, "active_today": False}
    assert me["total"] == 2  # the points stay


async def test_rejected_work_loses_its_day(client, admin, course, groups_setup):
    (_, curator, _, student), _ = groups_setup
    essay = await add_step(client, admin, course[1], free_text())
    sub = (await submit(client, student, essay, {"text": "x"})).json()["id"]
    assert (await rating(client, student))["streak"]["days"] == 1
    await client.post(
        f"/review/submissions/{sub}", json={"verdict": "rejected"}, headers=curator
    )
    assert (await rating(client, student))["streak"]["days"] == 0


async def test_days_follow_the_timezone(client, admin, course, groups_setup):
    """23:30 and 00:30 in Moscow are two days; in UTC they are one."""
    from config import settings
    from database import async_factory
    from progress.rating import streaks

    (_, _, student_id, student), _ = groups_setup
    steps = [
        await add_step(client, admin, course[1], single_choice()) for _ in range(2)
    ]
    evening = datetime(2026, 9, 20, 20, 30, tzinfo=UTC)  # 23:30 MSK
    # 23:30 MSK and 00:30 MSK next day, one solved step each.
    for step, when in zip(steps, (evening, evening + timedelta(hours=1)), strict=True):
        sub = (await submit(client, student, step, {"option_id": A})).json()["id"]
        await set_sent_at(sub, when)

    at = evening + timedelta(hours=2)
    async with async_factory() as db:
        moscow = await streaks(db, [student_id], [course[0]], at)
    assert moscow[student_id].days == 2
    old, settings.timezone = settings.timezone, "UTC"
    try:
        async with async_factory() as db:
            utc = await streaks(db, [student_id], [course[0]], at)
    finally:
        settings.timezone = old
    assert utc[student_id].days == 1


async def test_without_group_only_own_points(client, admin, course, make_user):
    step = await add_step(client, admin, course[1], single_choice())
    _, loner = await make_user()
    await submit(client, loner, step, {"option_id": A})
    me = await rating(client, loner)
    assert (me["total"], me["place"], me["group_size"]) == (4, None, None)
    assert me["next_place"] is None and me["first_place"] is None
    assert [o["step_id"] for o in me["opportunities"]] == []


async def test_unreachable_target(client, admin, course, make_user, groups_setup):
    (g1, _, _, leader), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice(max_attempts=1))
    _, me = await join(client, admin, make_user, g1)
    await submit(client, leader, step, {"option_id": A})  # 2 + 2 streak
    await submit(client, me, step, {"option_id": B})  # 0, no attempts left

    r = await rating(client, me)
    assert r["opportunities"] == []
    assert r["next_place"] == {
        "place": 1,
        "points": 4,
        "gap": 4,
        "plan": [],
        "reachable": False,
    }


async def test_enough_only_for_a_tie_is_unreachable(
    client, admin, course, make_user, groups_setup
):
    (g1, _, _, leader), _ = groups_setup
    a = await add_step(client, admin, course[1], single_choice())  # 2
    essay = await add_step(client, admin, course[1], free_text())
    _, me = await join(client, admin, make_user, g1)
    await submit(client, leader, a, {"option_id": A})  # leader: 2 + 2 = 4
    await submit(client, me, essay, {"text": "x"})  # me: waiting, streak: 2

    r = await rating(client, me)
    # All I can still get is A's 2 points: 4, only a tie with the leader.
    assert [o["step_id"] for o in r["opportunities"]] == [a]
    assert (r["next_place"]["gap"], r["next_place"]["reachable"]) == (2, False)


async def test_access(client, admin, ranked, groups_setup):
    url = f"/groups/{ranked['group']}/rating"
    assert (await client.get(url, headers=ranked["curator"])).status_code == 200
    assert (await client.get(url, headers=admin[1])).status_code == 200
    other_curator = groups_setup[1][1]
    assert (await client.get(url, headers=other_curator)).status_code == 403
    student = ranked["students"][0][1]
    assert (await client.get(url, headers=student)).status_code == 403
    # The personal rating is for students.
    assert (await client.get("/rating", headers=ranked["curator"])).status_code == 403
