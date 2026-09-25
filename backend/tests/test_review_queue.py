"""Review queue grouped by course: GET /review/courses."""

import pytest
from conftest import requires_db
from test_api import add_step, free_text, submit
from test_deadlines import PAST, put_deadline

pytestmark = requires_db


async def second_course(client, admin, student_ids):
    h = admin[1]
    course_id = (
        await client.post(
            "/admin/courses", json={"slug": "algo", "title": "Алгоритмы"}, headers=h
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
    await client.post(
        f"/admin/courses/{course_id}/enrollments",
        json={"user_ids": student_ids},
        headers=h,
    )
    return course_id, module_id


async def queue(client, headers, **params):
    r = await client.get("/review/courses", params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_queue_grouped_by_course(client, admin, course, groups_setup):
    (g1, curator1, student1_id, student1), (_, curator2, student2_id, student2) = (
        groups_setup
    )
    algo, algo_module = await second_course(client, admin, [student1_id, student2_id])
    py_step = await add_step(client, admin, course[1], free_text())
    py_step2 = await add_step(client, admin, course[1], free_text())
    algo_step = await add_step(client, admin, algo_module, free_text())
    # Only the first step is overdue: later steps do not inherit backwards.
    await put_deadline(client, curator1, g1, py_step, PAST)

    # Algorithms waits longest, so it comes first.
    s_algo = (await submit(client, student1, algo_step, {"text": "a"})).json()["id"]
    s_py1 = (await submit(client, student1, py_step, {"text": "b"})).json()["id"]
    s_py2 = (await submit(client, student1, py_step2, {"text": "c"})).json()["id"]
    await submit(client, student2, py_step, {"text": "other group"})

    mine = await queue(client, curator1)
    assert [(q["course_id"], q["course_title"]) for q in mine] == [
        (algo, "Алгоритмы"),
        (course[0], "Python"),
    ]
    assert [s["id"] for s in mine[0]["submissions"]] == [s_algo]
    python = mine[1]
    assert [s["id"] for s in python["submissions"]] == [s_py1, s_py2]
    assert (python["total"], python["late"]) == (2, 1)
    assert all(s["course_id"] == course[0] for s in python["submissions"])

    # Reviewed work leaves the queue; a course without work disappears.
    await client.post(
        f"/review/submissions/{s_algo}", json={"verdict": "accepted"}, headers=curator1
    )
    assert [q["course_id"] for q in await queue(client, curator1)] == [course[0]]

    # The other curator sees only their group; the admin sees everyone.
    theirs = await queue(client, curator2)
    assert [q["total"] for q in theirs] == [1]
    assert theirs[0]["submissions"][0]["student_id"] == student2_id
    assert [q["total"] for q in await queue(client, admin[1])] == [3]


async def test_queue_cut_keeps_totals_and_filters(client, admin, course, groups_setup):
    (_, curator, student_id, student), _ = groups_setup
    steps = [await add_step(client, admin, course[1], free_text()) for _ in range(3)]
    for step in steps:
        await submit(client, student, step, {"text": "x"})

    cut = await queue(client, curator, per_course=2)
    assert (cut[0]["total"], len(cut[0]["submissions"])) == (3, 2)
    assert await queue(client, curator, student_id=student_id + 1000) == []
    assert (await queue(client, curator, student_id=student_id))[0]["total"] == 3


async def test_queue_is_for_staff_only(client, make_user):
    _, student = await make_user()
    r = await client.get("/review/courses", headers=student)
    assert r.status_code == 403


async def sent_ago(sub_id, hours):
    from datetime import timedelta

    from sqlalchemy import update

    from courses.service import now
    from database import async_factory
    from submissions.models import Submission

    async with async_factory() as db, db.begin():
        await db.execute(
            update(Submission)
            .where(Submission.id == sub_id)
            .values(created_at=now() - timedelta(hours=hours))
        )


def about(seconds, hours):
    # A little slack for the time the request itself takes.
    return hours * 3600 <= seconds < hours * 3600 + 60


async def test_waiting_time(client, admin, course, groups_setup):
    (_, curator, _, student), _ = groups_setup
    steps = [await add_step(client, admin, course[1], free_text()) for _ in range(2)]
    old = (await submit(client, student, steps[0], {"text": "old"})).json()["id"]
    new = (await submit(client, student, steps[1], {"text": "new"})).json()["id"]
    await sent_ago(old, 3)

    python = (await queue(client, curator))[0]
    waiting = {s["id"]: s["waiting_seconds"] for s in python["submissions"]}
    assert about(waiting[old], 3) and about(waiting[new], 0)
    assert python["longest_waiting_seconds"] == waiting[old]

    flat = (await client.get("/review/submissions", headers=curator)).json()
    assert about(flat[0]["waiting_seconds"], 3)
    detail = await client.get(f"/review/submissions/{old}", headers=curator)
    assert about(detail.json()["waiting_seconds"], 3)

    # Reviewed work is not waiting any more.
    r = await client.post(
        f"/review/submissions/{old}", json={"verdict": "accepted"}, headers=curator
    )
    assert r.json()["waiting_seconds"] is None


def doc(*nodes):
    return {"type": "doc", "content": list(nodes)}


def heading(text, **attrs):
    return {
        "type": "heading",
        "attrs": {"level": 1, **attrs},
        "content": [{"type": "text", "text": text}],
    }


def para(*texts):
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": t} for t in texts],
    }


@pytest.mark.parametrize(
    ("content", "title"),
    [
        # The editor's title heading, in any step type's document field.
        (
            {"question": doc(heading("Чётность", zebra_title=True), para("x"))},
            "Чётность",
        ),
        ({"statement": doc(para("Условие"), heading("Парты"))}, "Парты"),
        (
            {"body": doc(para(""), para("Первая  строка", "текста"))},
            "Первая строка текста",
        ),
        ({"question": doc(para("я" * 150))}, "я" * 100),
        ({"question": doc()}, ""),
        ({"options": []}, ""),
    ],
)
def test_step_title(content, title):
    from submissions.review_api import get_step_title

    assert get_step_title(content) == title


async def test_queue_shows_step_title(client, admin, course, groups_setup):
    (_, curator, _, student), _ = groups_setup
    step = free_text()
    step["content"]["question"] = doc(heading("Эссе о циклах", zebra_title=True))
    step_id = await add_step(client, admin, course[1], step)
    sub_id = (await submit(client, student, step_id, {"text": "x"})).json()["id"]

    [python] = await queue(client, curator)
    assert python["submissions"][0]["task_title"] == "Эссе о циклах"
    detail = await client.get(f"/review/submissions/{sub_id}", headers=curator)
    assert detail.json()["task_title"] == "Эссе о циклах"
