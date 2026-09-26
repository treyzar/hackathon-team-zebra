"""Curator's learners: groups, students and their worst status over courses."""

from datetime import UTC, datetime, timedelta

from conftest import requires_db
from test_api import A, add_step, single_choice, submit
from test_deadlines import PAST, put_deadline
from test_rating import join

pytestmark = requires_db


async def published_course(client, admin, slug, title):
    h = admin[1]
    course_id = (
        await client.post(
            "/admin/courses", json={"slug": slug, "title": title}, headers=h
        )
    ).json()["id"]
    module_id = (
        await client.post(
            f"/admin/courses/{course_id}/modules", json={"title": "M"}, headers=h
        )
    ).json()["id"]
    await client.patch(
        f"/admin/courses/{course_id}", json={"is_published": True}, headers=h
    )
    return course_id, module_id


async def enroll(client, admin, course_id, user_ids):
    r = await client.post(
        f"/admin/courses/{course_id}/enrollments",
        json={"user_ids": user_ids},
        headers=admin[1],
    )
    assert r.status_code == 200, r.text


async def learners(client, headers):
    r = await client.get("/learners", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_worst_status_over_courses(
    client, admin, course, groups_setup, make_user
):
    (g1, curator1, s1_id, _), (g2, curator2, s2_id, _) = groups_setup
    s3_id, s3 = await join(client, admin, make_user, g1)
    s4_id, _ = await join(client, admin, make_user, g1, enroll=False)  # no courses
    algo, algo_module = await published_course(client, admin, "algo", "Алгоритмы")
    await enroll(client, admin, algo, [s1_id, s3_id])

    py_step = await add_step(client, admin, course[1], single_choice())
    algo_step = await add_step(client, admin, algo_module, single_choice())
    # Python: overdue by years; Algorithms: overdue by two days.
    await put_deadline(client, curator1, g1, py_step, PAST)
    recent = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    await put_deadline(client, curator1, g1, algo_step, recent)
    await submit(client, s3, py_step, {"option_id": A})  # s3 is fine in Python

    [group] = await learners(client, curator1)
    assert (group["group_id"], group["name"]) == (g1, "G0")
    rows = {s["student_id"]: s for s in group["students"]}
    assert set(rows) == {s1_id, s3_id, s4_id}

    one = rows[s1_id]
    assert [
        (c["course_id"], c["status"], c["overdue_steps"]) for c in one["courses"]
    ] == [
        (course[0], "falling_behind", 1),
        (algo, "slowed", 1),
    ]
    assert one["status"] == "falling_behind"
    assert [c["status"] for c in rows[s3_id]["courses"]] == ["on_track", "slowed"]
    assert rows[s3_id]["status"] == "slowed"
    assert (rows[s4_id]["status"], rows[s4_id]["courses"]) == (None, [])
    assert (one["name"], one["surname"]) == ("Имя", one["username"].capitalize())

    # Each curator sees their own groups; admins see all of them.
    [theirs] = await learners(client, curator2)
    assert theirs["group_id"] == g2
    assert [(s["student_id"], s["status"]) for s in theirs["students"]] == [
        (s2_id, "on_track")
    ]
    assert [g["group_id"] for g in await learners(client, admin[1])] == [g1, g2]


async def test_only_staff(client, groups_setup):
    (_, _, _, student), _ = groups_setup
    assert (await client.get("/learners", headers=student)).status_code == 403
