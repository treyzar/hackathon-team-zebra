"""Rating within a group: places, ties, anonymous targets and plans."""

import pytest
from conftest import requires_db
from test_api import DOC, A, B, add_step, multiple_choice, single_choice, submit

pytestmark = requires_db
THEORY = {"type": "theory", "content": {"body": DOC}}


async def rating(client, headers, course_id):
    r = await client.get(f"/courses/{course_id}/rating", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def join(client, admin, make_user, group_id):
    user_id, headers = await make_user()
    r = await client.put(
        f"/admin/groups/{group_id}/students/{user_id}", headers=admin[1]
    )
    assert r.status_code == 204
    return user_id, headers


@pytest.fixture
async def ranked(client, admin, course, make_user, groups_setup):
    """Group of four with points 6, 4, 4, 0 on steps A (2), B (4), C (2)."""
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


async def test_places_share_on_ties(client, course, ranked):
    (_, s1), (_, s2), (_, s3), (_, s4) = ranked["students"]
    got = [await rating(client, h, course[0]) for h in (s1, s2, s3, s4)]
    assert [(r["points"], r["place"], r["tied_with"]) for r in got] == [
        (6, 1, 0),
        (4, 2, 1),
        (4, 2, 1),
        (0, 4, 0),
    ]
    assert all(r["group_size"] == 4 for r in got)


async def test_first_place_sees_no_targets_above(client, course, ranked):
    me = await rating(client, ranked["students"][0][1], course[0])
    assert me["next_place"] is None
    assert me["first_place"] == {
        "place": 1,
        "points": 6,
        "gap": None,
        "plan": [],
        "reachable": True,
    }


async def test_targets_skip_equal_points(client, course, ranked):
    a, b, c = ranked["steps"]
    me = await rating(client, ranked["students"][1][1], course[0])  # 4, tied
    # The tie at 4 is skipped: the next place above is the 6 at place 1.
    assert me["next_place"] | {"plan": None} == {
        "place": 1,
        "points": 6,
        "gap": 2,
        "plan": None,
        "reachable": True,
    }
    # 2 more only ties; A (2) + C (2) = 4 > 2 overtakes.
    assert me["next_place"]["plan"] == [a, c]


async def test_plan_completes_first_then_improves(client, course, ranked):
    a, b, c = ranked["steps"]
    me = await rating(client, ranked["students"][2][1], course[0])  # A 2, B 2/4
    assert [
        (o["step_id"], o["action"], o["can_gain"]) for o in me["opportunities"]
    ] == [
        (c, "complete", 2),
        (b, "improve", 2),
    ]
    assert me["next_place"]["gap"] == 2 and me["next_place"]["plan"] == [c, b]
    # Where each step is, as the student sees the course.
    assert (
        me["opportunities"][0]["module_title"],
        me["opportunities"][0]["position"],
    ) == (
        "Intro",
        4,
    )


async def test_last_place_targets(client, course, ranked):
    a, b, c = ranked["steps"]
    me = await rating(client, ranked["students"][3][1], course[0])  # 0 points
    assert (me["next_place"]["place"], me["next_place"]["gap"]) == (2, 4)
    assert me["next_place"]["plan"] == [a, b]  # 2 + 4 = 6 > 4
    assert (me["first_place"]["points"], me["first_place"]["gap"]) == (6, 6)
    assert me["first_place"]["plan"] == [a, b, c]  # 6 only ties, 8 > 6


async def test_student_sees_no_one_else(client, course, ranked):
    leader = ranked["students"][0][1]
    leader_name = (await client.get("/user/me", headers=leader)).json()["username"]
    me = await rating(client, ranked["students"][3][1], course[0])
    # Only aggregates about others: no names, no ids of other students.
    assert leader_name not in str(me)
    assert set(me) == {
        "course_id",
        "group_size",
        "points",
        "place",
        "tied_with",
        "next_place",
        "first_place",
        "opportunities",
    }
    assert set(me["first_place"]) == {"place", "points", "gap", "plan", "reachable"}


async def test_unreachable_target(client, admin, course, make_user, groups_setup):
    (g1, _, _, leader), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice(max_attempts=1))
    _, me = await join(client, admin, make_user, g1)
    await submit(client, leader, step, {"option_id": A})  # 2
    await submit(client, me, step, {"option_id": B})  # 0, no attempts left

    r = await rating(client, me, course[0])
    assert r["opportunities"] == []
    assert r["next_place"] == {
        "place": 1,
        "points": 2,
        "gap": 2,
        "plan": [],
        "reachable": False,
    }


async def test_no_group_no_rating(client, course, make_user):
    _, loner = await make_user()
    r = await client.get(f"/courses/{course[0]}/rating", headers=loner)
    assert r.status_code == 404


async def test_curator_sees_group_rating(client, admin, course, ranked, groups_setup):
    (s1_id, _), (s2_id, _), (s3_id, _), (s4_id, _) = ranked["students"]
    url = f"/groups/{ranked['group']}/courses/{course[0]}/rating"
    rows = (await client.get(url, headers=ranked["curator"])).json()
    assert [(r["place"], r["student_id"], r["points"]) for r in rows] == [
        (1, s1_id, 6),
        *sorted([(2, s2_id, 4), (2, s3_id, 4)], key=lambda x: x[1]),
        (4, s4_id, 0),
    ]
    assert all(r["username"] for r in rows)

    other_curator = groups_setup[1][1]
    assert (await client.get(url, headers=other_curator)).status_code == 403
    student = ranked["students"][0][1]
    assert (await client.get(url, headers=student)).status_code == 403
    assert (await client.get(url, headers=admin[1])).status_code == 200


async def test_enough_only_for_a_tie_is_unreachable(
    client, admin, course, make_user, groups_setup
):
    (g1, _, _, leader), _ = groups_setup
    a = await add_step(client, admin, course[1], single_choice())  # 2
    c = await add_step(client, admin, course[1], single_choice(max_attempts=1))
    _, me = await join(client, admin, make_user, g1)
    await submit(client, leader, a, {"option_id": A})  # leader: 2
    await submit(client, me, c, {"option_id": B})  # me: 0, c closed

    r = await rating(client, me, course[0])
    # All I can still get is A's 2 points: that equals the leader, a tie at
    # best, so overtaking is not reachable.
    assert [o["step_id"] for o in r["opportunities"]] == [a]
    assert (r["next_place"]["gap"], r["next_place"]["reachable"]) == (2, False)
