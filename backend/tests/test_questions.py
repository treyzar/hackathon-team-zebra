"""Questions about steps: who asks, who sees, who answers."""

from conftest import requires_db
from test_access import make_sequential
from test_api import add_step, single_choice

pytestmark = requires_db


async def ask(client, headers, step_id, text="Почему ответ 0?"):
    return await client.post(
        f"/steps/{step_id}/questions", json={"text": text}, headers=headers
    )


async def seen(client, headers, step_id):
    r = await client.get(f"/steps/{step_id}/questions", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def staff_list(client, headers, **params):
    r = await client.get("/questions", params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def patch(client, headers, question_id, **body):
    return await client.patch(f"/questions/{question_id}", json=body, headers=headers)


async def notifications(client, headers, type_):
    items = (await client.get("/notifications", headers=headers)).json()
    return [n["payload"] for n in items if n["type"] == type_]


async def classmate_of(client, admin, make_user, group_id):
    student_id, headers = await make_user()
    r = await client.put(
        f"/admin/groups/{group_id}/students/{student_id}", headers=admin[1]
    )
    assert r.status_code == 204
    return headers


async def test_private_question_and_answer(
    client, admin, course, groups_setup, make_user
):
    (g1, curator1, s1_id, s1), (_, curator2, _, s2) = groups_setup
    classmate = await classmate_of(client, admin, make_user, g1)
    step = await add_step(client, admin, course[1], single_choice())

    r = await ask(client, s1, step)
    assert r.status_code == 201, r.text
    q = r.json()
    assert (q["is_mine"], q["visibility"], q["answer"]) == (True, "private", None)
    assert await notifications(client, curator1, "question_asked") == [
        {
            "question_id": q["id"],
            "step_id": step,
            "course_id": course[0],
            "student_id": s1_id,
        }
    ]

    # Private: the author, their curator and admins only.
    assert [x["id"] for x in await seen(client, s1, step)] == [q["id"]]
    assert await seen(client, classmate, step) == []
    assert await seen(client, s2, step) == []
    mine = await staff_list(client, curator1)
    assert [(x["id"], x["author_id"], x["can_answer"]) for x in mine] == [
        (q["id"], s1_id, True)
    ]
    assert mine[0]["waiting_seconds"] is not None
    assert await staff_list(client, curator2) == []
    assert len(await staff_list(client, admin[1])) == 1

    # Other group's curator: the question does not exist for them.
    assert (await patch(client, curator2, q["id"], answer="x")).status_code == 404
    assert (await patch(client, s1, q["id"], answer="x")).status_code == 403

    r = await patch(client, curator1, q["id"], answer="Нуль — чётное число.")
    assert r.status_code == 200, r.text
    assert (r.json()["answer"], r.json()["waiting_seconds"]) == (
        "Нуль — чётное число.",
        None,
    )
    assert (await seen(client, s1, step))[0]["answer"] == "Нуль — чётное число."
    assert await seen(client, classmate, step) == []  # answered, still private
    assert await staff_list(client, curator1, answered=False) == []

    # One notification, even when the answer is corrected later.
    await patch(client, curator1, q["id"], answer="Исправленный ответ")
    assert await notifications(client, s1, "question_answered") == [
        {"question_id": q["id"], "step_id": step, "course_id": course[0]}
    ]


async def test_open_to_group_hides_author(
    client, admin, course, groups_setup, make_user
):
    (g1, curator1, s1_id, s1), (g2, _, _, s2) = groups_setup
    classmate = await classmate_of(client, admin, make_user, g1)
    step = await add_step(client, admin, course[1], single_choice())
    q = (await ask(client, s1, step)).json()

    r = await patch(client, curator1, q["id"], answer="Ответ", visibility="group")
    assert (r.json()["visibility"], r.json()["group_id"]) == ("group", g1)

    [shown] = await seen(client, classmate, step)
    assert (shown["id"], shown["is_mine"], shown["answer"]) == (q["id"], False, "Ответ")
    # Nothing tells who asked: exactly these fields, none about the author.
    assert set(shown) == {
        "id",
        "step_id",
        "text",
        "created_at",
        "is_mine",
        "visibility",
        "answer",
        "answered_at",
    }
    assert await seen(client, s2, step) == []

    # The question stays with the group it was opened to.
    await client.put(f"/admin/groups/{g2}/students/{s1_id}", headers=admin[1])
    assert [x["id"] for x in await seen(client, classmate, step)] == [q["id"]]
    assert await seen(client, s2, step) == []
    assert [x["is_mine"] for x in await seen(client, s1, step)] == [True]


async def test_open_to_everyone(client, admin, course, groups_setup):
    (_, curator1, _, s1), (_, curator2, _, s2) = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    q = (await ask(client, s1, step)).json()

    # Only an answered question may be opened.
    r = await patch(client, curator1, q["id"], visibility="course")
    assert r.status_code == 422
    assert (await seen(client, s2, step)) == []

    await patch(client, curator1, q["id"], answer="Ответ", visibility="course")
    assert [x["id"] for x in await seen(client, s2, step)] == [q["id"]]
    # Another group's curator reads it, but may not change it.
    [theirs] = await staff_list(client, curator2)
    assert (theirs["id"], theirs["can_answer"]) == (q["id"], False)
    assert (await patch(client, curator2, q["id"], answer="x")).status_code == 403
    r = await client.delete(f"/questions/{q['id']}", headers=curator2)
    assert r.status_code == 403

    # Back to private: only the author again.
    await patch(client, curator1, q["id"], visibility="private")
    assert await seen(client, s2, step) == []
    assert await staff_list(client, curator2) == []


async def test_group_visibility_needs_a_group(client, admin, course, make_user):
    step = await add_step(client, admin, course[1], single_choice())
    _, loner = await make_user()
    q = (await ask(client, loner, step)).json()
    r = await patch(client, admin[1], q["id"], answer="Ответ", visibility="group")
    assert r.status_code == 422
    # Nothing was saved by the failed request.
    [row] = await staff_list(client, admin[1])
    assert (row["answer"], row["visibility"]) == (None, "private")


async def test_who_may_ask(client, admin, course, groups_setup, make_user):
    (_, curator, _, student), _ = groups_setup
    first = await add_step(client, admin, course[1], single_choice())
    second = await add_step(client, admin, course[1], single_choice())

    assert (await ask(client, curator, first)).status_code == 403
    assert (await ask(client, admin[1], first)).status_code == 403
    _, outsider = await make_user(enroll=False)
    assert (await ask(client, outsider, first)).status_code == 404
    assert (await ask(client, student, first, text="   ")).status_code == 422

    await make_sequential(client, admin, course)
    assert (await ask(client, student, second)).status_code == 403
    r = await client.get(f"/steps/{second}/questions", headers=student)
    assert r.status_code == 403
    await client.patch(
        f"/admin/steps/{first}", json={"is_hidden": True}, headers=admin[1]
    )
    assert (await ask(client, student, first)).status_code == 404


async def test_update_body_and_filters(client, admin, course, groups_setup):
    (_, curator, s1_id, s1), (_, _, _, s2) = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    q1 = (await ask(client, s1, step, "первый")).json()
    q2 = (await ask(client, s2, step, "второй")).json()

    assert (await patch(client, curator, q1["id"])).status_code == 422
    assert (await patch(client, curator, q1["id"], answer=None)).status_code == 422
    assert (await patch(client, curator, q1["id"], answer="  ")).status_code == 422

    await patch(client, admin[1], q2["id"], answer="Ответ")
    everyone = await staff_list(client, admin[1])
    assert [x["text"] for x in everyone] == ["первый", "второй"]
    waiting = await staff_list(client, admin[1], answered=False)
    assert [x["id"] for x in waiting] == [q1["id"]]
    assert [x["id"] for x in await staff_list(client, admin[1], answered=True)] == [
        q2["id"]
    ]
    assert [x["id"] for x in await staff_list(client, admin[1], student_id=s1_id)] == [
        q1["id"]
    ]
    assert await staff_list(client, admin[1], course_id=course[0] + 1) == []
    assert len(await staff_list(client, admin[1], step_id=step)) == 2


async def test_delete_and_deleted_step(client, admin, course, groups_setup):
    (_, curator, _, student), _ = groups_setup
    step = await add_step(client, admin, course[1], single_choice())
    q1 = (await ask(client, student, step)).json()
    q2 = (await ask(client, student, step)).json()

    assert (
        await client.delete(f"/questions/{q1['id']}", headers=curator)
    ).status_code == 204
    assert [x["id"] for x in await seen(client, student, step)] == [q2["id"]]

    # A deleted step takes its questions out of sight.
    await client.delete(f"/admin/steps/{step}", headers=admin[1])
    assert await staff_list(client, curator) == []
    assert (await patch(client, curator, q2["id"], answer="x")).status_code == 404
