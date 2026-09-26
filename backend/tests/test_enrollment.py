"""Enrollment: students see only the courses an admin enrolled them in."""

from conftest import requires_db
from test_api import A, add_step, single_choice, submit

pytestmark = requires_db


async def enroll(client, admin, course_id, user_ids=(), group_ids=()):
    return await client.post(
        f"/admin/courses/{course_id}/enrollments",
        json={"user_ids": list(user_ids), "group_ids": list(group_ids)},
        headers=admin[1],
    )


async def sees_course(client, headers, course_id) -> bool:
    listed = [c["id"] for c in (await client.get("/courses", headers=headers)).json()]
    r = await client.get(f"/courses/{course_id}", headers=headers)
    assert (course_id in listed) == (r.status_code == 200)
    return r.status_code == 200


async def test_not_enrolled_student_sees_nothing(client, admin, course, make_user):
    step = await add_step(client, admin, course[1], single_choice())
    _, h = await make_user(enroll=False)

    assert (await client.get("/courses", headers=h)).json() == []
    # Everywhere the course is simply not there.
    for r in (
        await client.get(f"/courses/{course[0]}", headers=h),
        await client.get(f"/steps/{step}", headers=h),
        await client.get(f"/steps/{step}/submissions", headers=h),
        await submit(client, h, step, {"option_id": A}),
        await client.get(f"/courses/{course[0]}/progress", headers=h),
    ):
        assert r.status_code == 404, r.request.url


async def test_staff_see_every_course(client, admin, course, make_user):
    for role in ("curator", "admin"):
        _, h = await make_user(role)
        assert await sees_course(client, h, course[0])


async def test_enroll_students_by_id(client, admin, course, make_user):
    s1, h1 = await make_user(enroll=False)
    s2, _ = await make_user(enroll=False)
    r = await enroll(client, admin, course[0], user_ids=[s1, s2])
    assert r.json() == {"enrolled": sorted([s1, s2]), "already_enrolled": []}
    assert await sees_course(client, h1, course[0])

    again = await enroll(client, admin, course[0], user_ids=[s1])
    assert again.json() == {"enrolled": [], "already_enrolled": [s1]}


async def test_enroll_groups_is_a_snapshot(client, admin, course, make_user):
    s1, h1 = await make_user(enroll=False)
    s2, _ = await make_user(enroll=False)
    g = (
        await client.post("/admin/groups", json={"name": "G"}, headers=admin[1])
    ).json()
    for s in (s1, s2):
        await client.put(f"/admin/groups/{g['id']}/students/{s}", headers=admin[1])
    # A group and a student of it at once: enrolled once.
    r = await enroll(client, admin, course[0], user_ids=[s1], group_ids=[g["id"]])
    assert r.json()["enrolled"] == sorted([s1, s2])
    assert await sees_course(client, h1, course[0])

    # Who joins the group later is not enrolled automatically.
    s3, h3 = await make_user(enroll=False)
    await client.put(f"/admin/groups/{g['id']}/students/{s3}", headers=admin[1])
    assert not await sees_course(client, h3, course[0])

    listed = (
        await client.get(f"/admin/courses/{course[0]}/enrollments", headers=admin[1])
    ).json()
    assert {(s["id"], s["group_id"]) for s in listed} == {(s1, g["id"]), (s2, g["id"])}


async def test_enroll_validation_and_access(client, admin, course, make_user):
    curator_id, curator = await make_user("curator")
    _, student = await make_user()
    url = f"/admin/courses/{course[0]}/enrollments"
    for body in ({"user_ids": [curator_id]}, {"user_ids": [999]}, {"group_ids": [999]}):
        r = await client.post(url, json=body, headers=admin[1])
        assert r.status_code == 422, body
    for h in (curator, student):
        assert (await client.post(url, json={}, headers=h)).status_code == 403
        assert (await client.get(url, headers=h)).status_code == 403


async def test_unenroll_keeps_results(client, admin, course, make_user):
    step = await add_step(client, admin, course[1], single_choice())
    sid, h = await make_user(enroll=False)
    await enroll(client, admin, course[0], user_ids=[sid])
    await submit(client, h, step, {"option_id": A})

    url = f"/admin/courses/{course[0]}/enrollments/{sid}"
    assert (await client.delete(url, headers=admin[1])).status_code == 204
    assert not await sees_course(client, h, course[0])
    assert (await client.delete(url, headers=admin[1])).status_code == 404

    await enroll(client, admin, course[0], user_ids=[sid])
    p = (await client.get(f"/courses/{course[0]}/progress", headers=h)).json()
    assert (p["steps_completed"], p["points_earned"]) == (1, 2)


async def test_group_views_count_only_enrolled(
    client, admin, course, groups_setup, make_user
):
    (group_id, curator, enrolled_id, enrolled), _ = groups_setup
    outsider_id, _ = await make_user(enroll=False)
    await client.put(
        f"/admin/groups/{group_id}/students/{outsider_id}", headers=admin[1]
    )

    base = f"/groups/{group_id}/courses/{course[0]}"
    progress = (await client.get(f"{base}/progress", headers=curator)).json()
    assert [r["student_id"] for r in progress] == [enrolled_id]
    # The rating is per group, over each student's own courses: a groupmate
    # not enrolled here is ranked with none of this course's points.
    rating = (await client.get(f"/groups/{group_id}/rating", headers=curator)).json()
    courses = {r["student_id"]: [c["course_id"] for c in r["courses"]] for r in rating}
    assert courses == {enrolled_id: [course[0]], outsider_id: []}
