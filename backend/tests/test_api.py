"""End-to-end API scenarios against a real Postgres (TEST_DB_URL)."""

import uuid

import pytest
from conftest import requires_db

pytestmark = requires_db

A, B = str(uuid.uuid4()), str(uuid.uuid4())
DOC = {"type": "doc", "content": []}


def single_choice(**settings):
    return {
        "type": "single_choice",
        "max_score": 2,
        "content": {
            "question": DOC,
            "options": [{"id": A, "text": "yes"}, {"id": B, "text": "no"}],
        },
        "answer_key": {"correct": A},
        "settings": settings,
    }


def free_text(**content):
    return {
        "type": "free_text",
        "max_score": 5,
        "content": {"question": DOC, **content},
        "answer_key": {"criteria": "mentions X"},
    }


def programming(grading="tests", scoring="all_or_nothing", max_score=10):
    return {
        "type": "programming",
        "max_score": max_score,
        "content": {
            "statement": DOC,
            "samples": [{"input": "2\n", "output": "4"}],
        },
        "answer_key": {
            "test_groups": [
                {
                    "name": "pos",
                    "points": 4,
                    "tests": [{"input": "3\n", "output": "9"}],
                },
                {
                    "name": "neg",
                    "points": 6,
                    "tests": [{"input": "-3\n", "output": "9"}],
                },
            ],
            "reference_solution": "print(int(input()) ** 2)",
        },
        "settings": {"grading": grading, "scoring": scoring},
    }


async def add_step(client, admin, module_id, payload) -> int:
    r = await client.post(
        f"/admin/modules/{module_id}/steps", json={"payload": payload}, headers=admin[1]
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def submit(client, headers, step_id, answer):
    return await client.post(
        f"/steps/{step_id}/submissions", json={"answer": answer}, headers=headers
    )


async def test_only_admin_authors(client, make_user):
    for role in ("student", "curator"):
        _, h = await make_user(role)
        r = await client.post(
            "/admin/courses", json={"slug": "x", "title": "X"}, headers=h
        )
        assert r.status_code == 403


async def test_student_never_gets_answer_key(client, admin, course, make_user):
    step_id = await add_step(client, admin, course[1], single_choice())
    _, h = await make_user()
    r = await client.get(f"/steps/{step_id}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert "answer_key" not in body and A in str(body["content"])
    assert "correct" not in str(body)


async def test_auto_grading_attempts_and_answer(client, admin, course, make_user):
    step_id = await add_step(
        client,
        admin,
        course[1],
        single_choice(max_attempts=2, show_answer="after_wrong"),
    )
    _, h = await make_user()

    assert (await client.get(f"/steps/{step_id}/answer", headers=h)).status_code == 403
    r = await submit(client, h, step_id, {"option_id": B})
    assert (r.json()["status"], r.json()["score"]) == ("wrong", 0)
    assert (await client.get(f"/steps/{step_id}/answer", headers=h)).json() == {
        "correct": A
    }
    r = await submit(client, h, step_id, {"option_id": A})
    assert (r.json()["status"], r.json()["score"]) == ("correct", 2)
    r = await submit(client, h, step_id, {"option_id": A})
    assert r.status_code == 409  # attempts exhausted

    step = (await client.get(f"/steps/{step_id}", headers=h)).json()
    assert step["attempts_used"] == 2
    assert step["progress"] == {"state": "solved", "best_score": 2}
    course_view = (await client.get(f"/courses/{course[0]}", headers=h)).json()
    assert course_view["modules"][0]["steps"][0]["progress"]["state"] == "solved"


async def test_invalid_answer_is_422(client, admin, course, make_user):
    step_id = await add_step(client, admin, course[1], single_choice())
    _, h = await make_user()
    r = await submit(client, h, step_id, {"option_id": str(uuid.uuid4())})
    assert r.status_code == 422
    r = await submit(client, h, step_id, {"wrong_field": 1})
    assert r.status_code == 422


async def test_visibility(client, admin, course, make_user):
    course_id, module_id = course
    step_id = await add_step(client, admin, module_id, single_choice())
    _, h = await make_user()
    await client.patch(
        f"/admin/steps/{step_id}", json={"is_hidden": True}, headers=admin[1]
    )
    assert (await client.get(f"/steps/{step_id}", headers=h)).status_code == 404
    await client.patch(
        f"/admin/steps/{step_id}", json={"is_hidden": False}, headers=admin[1]
    )
    await client.patch(
        f"/admin/courses/{course_id}", json={"is_published": False}, headers=admin[1]
    )
    assert (await client.get(f"/steps/{step_id}", headers=h)).status_code == 404
    assert (await client.get(f"/courses/{course_id}", headers=h)).status_code == 404
    assert (await client.get("/courses", headers=h)).json() == []


async def test_revisions_history_and_breaking_change(client, admin, course, make_user):
    step_id = await add_step(client, admin, course[1], single_choice())
    _, h = await make_user()
    await submit(client, h, step_id, {"option_id": A})

    new = single_choice()
    new["answer_key"] = {"correct": B}
    r = await client.post(
        f"/admin/steps/{step_id}/revisions",
        json={"payload": new, "base_revision": 7},
        headers=admin[1],
    )
    assert r.status_code == 409  # stale base revision
    r = await client.post(
        f"/admin/steps/{step_id}/revisions",
        json={
            "payload": new,
            "base_revision": 1,
            "is_breaking": True,
            "comment": "fix",
        },
        headers=admin[1],
    )
    assert r.json()["revision"]["number"] == 2

    history = (
        await client.get(f"/admin/steps/{step_id}/revisions", headers=admin[1])
    ).json()
    assert [(x["number"], x["comment"]) for x in history] == [(2, "fix"), (1, None)]
    old = await client.get(f"/admin/steps/{step_id}/revisions/1", headers=admin[1])
    assert old.json()["answer_key"] == {"correct": A}

    # The earlier (correct under rev 1) submission no longer counts.
    subs = (await client.get(f"/steps/{step_id}/submissions", headers=h)).json()
    assert subs[0]["is_outdated"]
    step = (await client.get(f"/steps/{step_id}", headers=h)).json()
    assert step["progress"]["state"] == "none" and step["attempts_used"] == 0

    wrong_type = {"type": "theory", "content": {"body": DOC}}
    r = await client.post(
        f"/admin/steps/{step_id}/revisions",
        json={"payload": wrong_type},
        headers=admin[1],
    )
    assert r.status_code == 422


async def test_reorder_steps(client, admin, course):
    ids = [await add_step(client, admin, course[1], single_choice()) for _ in range(3)]
    r = await client.put(
        f"/admin/modules/{course[1]}/steps/order",
        json={"ids": ids[::-1]},
        headers=admin[1],
    )
    assert r.status_code == 204
    tree = (await client.get(f"/admin/courses/{course[0]}", headers=admin[1])).json()
    assert [s["id"] for s in tree["modules"][0]["steps"]] == ids[::-1]
    r = await client.put(
        f"/admin/modules/{course[1]}/steps/order",
        json={"ids": ids[:2]},
        headers=admin[1],
    )
    assert r.status_code == 422


async def test_manual_review_scoped_by_group(client, admin, course, groups_setup):
    step_id = await add_step(client, admin, course[1], free_text())
    (_, curator1, _, student1), (_, curator2, _, _) = groups_setup

    r = await submit(client, student1, step_id, {"text": "my essay"})
    assert r.json()["status"] == "pending_review"
    sub_id = r.json()["id"]
    assert (
        await submit(client, student1, step_id, {"text": "again"})
    ).status_code == 409

    # The other group's curator sees nothing.
    assert (await client.get("/review/submissions", headers=curator2)).json() == []
    r = await client.get(f"/review/submissions/{sub_id}", headers=curator2)
    assert r.status_code == 404
    r = await client.post(
        f"/review/submissions/{sub_id}", json={"verdict": "accepted"}, headers=curator2
    )
    assert r.status_code == 404

    queue = (await client.get("/review/submissions", headers=curator1)).json()
    assert [x["id"] for x in queue] == [sub_id]
    detail = (
        await client.get(f"/review/submissions/{sub_id}", headers=curator1)
    ).json()
    assert detail["answer_key"]["criteria"] == "mentions X"

    r = await client.post(
        f"/review/submissions/{sub_id}",
        json={"verdict": "accepted", "score": 9},
        headers=curator1,
    )
    assert r.status_code == 422  # above max_score
    r = await client.post(
        f"/review/submissions/{sub_id}",
        json={"verdict": "accepted", "comment": "good"},
        headers=curator1,
    )
    assert (r.json()["status"], r.json()["score"]) == ("accepted", 5)
    mine = (await client.get(f"/submissions/{sub_id}", headers=student1)).json()
    assert mine["review_comment"] == "good"

    # Admin sees every group.
    all_subs = await client.get("/review/submissions?status=accepted", headers=admin[1])
    assert len(all_subs.json()) == 1


async def test_group_rules(client, admin, make_user, groups_setup):
    (g1, _, student_id, _), (g2, _, _, _) = groups_setup
    curator_id, _ = await make_user("curator")
    r = await client.put(f"/admin/groups/{g1}/students/{curator_id}", headers=admin[1])
    assert r.status_code == 422  # not a student

    # Moving a student to another group.
    await client.put(f"/admin/groups/{g2}/students/{student_id}", headers=admin[1])
    g1_students = (
        await client.get(f"/admin/groups/{g1}/students", headers=admin[1])
    ).json()
    assert g1_students == []

    # Promoting the student removes their membership.
    await client.patch(
        f"/admin/users/{student_id}/role", json={"role": "curator"}, headers=admin[1]
    )
    g2_students = (
        await client.get(f"/admin/groups/{g2}/students", headers=admin[1])
    ).json()
    assert student_id not in [s["id"] for s in g2_students]
    assert len(g2_students) == 1  # the group's own student stays


async def run_worker(monkeypatch, judge):
    import worker

    while (sub_id := await worker.claim_next()) is not None:
        await worker.process(sub_id, judge)


async def test_programming_tests_only(client, admin, course, make_user, local_judge):
    step_id = await add_step(client, admin, course[1], programming(scoring="per_group"))
    _, h = await make_user()
    r = await submit(
        client, h, step_id, {"code": "n=int(input())\nprint(n*n if n>0 else 0)"}
    )
    assert r.json()["status"] == "queued"
    sub_id = r.json()["id"]
    r = await submit(client, h, step_id, {"code": "print(1)"})
    assert r.status_code == 409  # previous one is still being checked

    await run_worker(None, local_judge)
    sub = (await client.get(f"/submissions/{sub_id}", headers=h)).json()
    assert (sub["status"], sub["score"]) == ("partial", 4)
    assert sub["result_details"]["samples"][0]["verdict"] == "ok"


async def test_programming_tests_and_review(
    client, admin, course, groups_setup, local_judge
):
    step_id = await add_step(
        client, admin, course[1], programming(grading="tests_and_review")
    )
    (_, curator, _, student) = groups_setup[0]
    r = await submit(client, student, step_id, {"code": "print(int(input()) ** 2)"})
    sub_id = r.json()["id"]
    await run_worker(None, local_judge)

    detail = (await client.get(f"/review/submissions/{sub_id}", headers=curator)).json()
    assert (detail["status"], detail["auto_score"], detail["score"]) == (
        "pending_review",
        10,
        None,
    )
    r = await client.post(
        f"/review/submissions/{sub_id}",
        json={"verdict": "accepted", "score": 7, "comment": "style"},
        headers=curator,
    )
    assert (r.json()["status"], r.json()["score"]) == ("accepted", 7)


async def test_judge_failure_is_retried_then_error(
    client, admin, course, make_user, monkeypatch
):
    from judge import JudgeError

    class BrokenJudge:
        async def run(self, *args, **kwargs):
            raise JudgeError("down")

    step_id = await add_step(client, admin, course[1], programming())
    _, h = await make_user()
    sub_id = (await submit(client, h, step_id, {"code": "print(1)"})).json()["id"]
    await run_worker(None, BrokenJudge())
    sub = (await client.get(f"/submissions/{sub_id}", headers=h)).json()
    assert sub["status"] == "error"
    # A judge failure is not an attempt and does not block a new submission.
    step = (await client.get(f"/steps/{step_id}", headers=h)).json()
    assert step["attempts_used"] == 0
    assert (await submit(client, h, step_id, {"code": "print(1)"})).status_code == 201


async def test_theory_marks_done(client, admin, course, make_user):
    step_id = await add_step(
        client, admin, course[1], {"type": "theory", "content": {"body": DOC}}
    )
    _, h = await make_user()
    r = await submit(client, h, step_id, {})
    assert (r.json()["status"], r.json()["score"]) == ("correct", 0)


async def test_files_access(client, admin, course, groups_setup, monkeypatch):
    from files import storage

    async def fake_size(key):
        return 10

    monkeypatch.setattr(storage, "object_size", fake_size)
    (_, curator1, _, student1), (_, curator2, _, student2) = groups_setup

    req = {"filename": "a.png", "mime": "image/png", "size": 10, "purpose": "content"}
    assert (await client.post("/files", json=req, headers=student1)).status_code == 403

    req["purpose"] = "submission"
    r = await client.post("/files", json=req, headers=student1)
    assert r.status_code == 201 and r.json()["upload_url"].startswith("http")
    file_id = r.json()["id"]
    r = await client.post(f"/files/{file_id}/complete", headers=student2)
    assert r.status_code == 404  # not the owner
    r = await client.post(f"/files/{file_id}/complete", headers=student1)
    assert r.json()["status"] == "ready"

    assert (await client.get(f"/files/{file_id}", headers=curator1)).status_code == 200
    assert (await client.get(f"/files/{file_id}", headers=curator2)).status_code == 404
    assert (await client.get(f"/files/{file_id}", headers=student2)).status_code == 404

    step_id = await add_step(
        client, admin, course[1], free_text(max_files=1, allowed_mime=["image/png"])
    )
    r = await submit(client, student2, step_id, {"files": [file_id]})
    assert r.status_code == 422  # someone else's file
    r = await submit(client, student1, step_id, {"files": [file_id]})
    assert r.status_code == 201, r.text


def multiple_choice(**settings):
    c = str(uuid.uuid4())
    return {
        "type": "multiple_choice",
        "max_score": 4,
        "content": {
            "question": DOC,
            "options": [
                {"id": A, "text": "a"},
                {"id": B, "text": "b"},
                {"id": c, "text": "c"},
            ],
        },
        "answer_key": {"correct": [A, B]},
        "settings": {"scoring": "partial", **settings},
    }


async def step_state(client, headers, step_id):
    s = (await client.get(f"/steps/{step_id}", headers=headers)).json()
    return s["can_submit"], s["submit_block_reason"]


async def test_resubmit_until_max_score(client, admin, course, make_user):
    step_id = await add_step(client, admin, course[1], multiple_choice())
    _, h = await make_user()
    assert await step_state(client, h, step_id) == (True, None)

    r = await submit(client, h, step_id, {"option_ids": [A]})
    assert (r.json()["status"], r.json()["score"]) == ("partial", 2)
    assert await step_state(client, h, step_id) == (True, None)

    r = await submit(client, h, step_id, {"option_ids": [A, B]})
    assert (r.json()["status"], r.json()["score"]) == ("correct", 4)
    # Maximum reached: no more attempts even though they are unlimited.
    can, reason = await step_state(client, h, step_id)
    assert not can and "maximum score" in reason
    r = await submit(client, h, step_id, {"option_ids": [A, B]})
    assert r.status_code == 409 and "maximum score" in r.json()["detail"]


async def test_attempt_limit_without_max_score(client, admin, course, make_user):
    step_id = await add_step(client, admin, course[1], multiple_choice(max_attempts=2))
    _, h = await make_user()
    for _ in range(2):
        assert (
            await submit(client, h, step_id, {"option_ids": [A]})
        ).status_code == 201
    assert await step_state(client, h, step_id) == (False, "No attempts left")
    assert (await submit(client, h, step_id, {"option_ids": [A, B]})).status_code == 409


async def test_breaking_change_reopens_step(client, admin, course, make_user):
    step_id = await add_step(client, admin, course[1], multiple_choice())
    _, h = await make_user()
    await submit(client, h, step_id, {"option_ids": [A, B]})
    assert (await step_state(client, h, step_id))[0] is False

    r = await client.post(
        f"/admin/steps/{step_id}/revisions",
        json={"payload": multiple_choice(), "is_breaking": True},
        headers=admin[1],
    )
    assert r.status_code == 200
    # The old full score is outdated, so the student may answer again.
    assert await step_state(client, h, step_id) == (True, None)


async def test_manual_review_score_decides(client, admin, course, groups_setup):
    step_id = await add_step(client, admin, course[1], free_text())
    (_, curator, _, student) = groups_setup[0]

    sub_id = (await submit(client, student, step_id, {"text": "v1"})).json()["id"]
    can, reason = await step_state(client, student, step_id)
    assert not can and "being checked" in reason
    await client.post(
        f"/review/submissions/{sub_id}",
        json={"verdict": "accepted", "score": 3},
        headers=curator,
    )
    # Accepted, but 3 of 5: the student may improve the answer.
    assert await step_state(client, student, step_id) == (True, None)

    sub_id = (await submit(client, student, step_id, {"text": "v2"})).json()["id"]
    await client.post(
        f"/review/submissions/{sub_id}", json={"verdict": "accepted"}, headers=curator
    )
    assert (await step_state(client, student, step_id))[0] is False


async def test_theory_is_viewed_once(client, admin, course, make_user):
    step_id = await add_step(
        client, admin, course[1], {"type": "theory", "content": {"body": DOC}}
    )
    _, h = await make_user()
    assert (await submit(client, h, step_id, {})).status_code == 201
    assert (await step_state(client, h, step_id))[0] is False
    assert (await submit(client, h, step_id, {})).status_code == 409


async def test_answer_with_required_text_and_photo(
    client, admin, course, make_user, upload
):
    step_id = await add_step(
        client,
        admin,
        course[1],
        free_text(
            require_text=True, min_files=1, max_files=2, allowed_mime=["image/png"]
        ),
    )
    _, h = await make_user()
    photo = await upload(h, b"\x89PNG...", purpose="submission", mime="image/png")

    r = await submit(client, h, step_id, {"text": "only text"})
    assert r.status_code == 422 and "at least 1" in r.text
    r = await submit(client, h, step_id, {"files": [photo]})
    assert r.status_code == 422 and "must contain text" in r.text
    r = await submit(client, h, step_id, {"text": "see photo", "files": [photo]})
    assert r.status_code == 201 and r.json()["status"] == "pending_review"


async def test_min_files_above_max_rejected(client, admin, course):
    r = await client.post(
        f"/admin/modules/{course[1]}/steps",
        json={"payload": free_text(min_files=3, max_files=1)},
        headers=admin[1],
    )
    assert r.status_code == 422


async def test_free_text_answer_shows_reference_only(
    client, admin, course, groups_setup
):
    step = free_text()
    step["answer_key"] = {"reference": DOC, "criteria": "for curators"}
    step["settings"] = {"show_answer": "after_solved"}
    step_id = await add_step(client, admin, course[1], step)
    (_, curator, _, student) = groups_setup[0]

    sub_id = (await submit(client, student, step_id, {"text": "answer"})).json()["id"]
    assert (
        await client.get(f"/steps/{step_id}/answer", headers=student)
    ).status_code == 403
    await client.post(
        f"/review/submissions/{sub_id}", json={"verdict": "accepted"}, headers=curator
    )
    r = await client.get(f"/steps/{step_id}/answer", headers=student)
    assert r.json() == {"reference": DOC}


async def test_partial_score_is_explained(client, admin, course, make_user):
    step_id = await add_step(client, admin, course[1], multiple_choice())
    _, h = await make_user()
    r = (await submit(client, h, step_id, {"option_ids": [A]})).json()
    assert r["score"] == 2
    assert r["result_details"] == {
        "correct_picked": 1,
        "wrong_picked": 0,
        "correct_total": 2,
    }
    # show_answer is "never": no per-option breakdown.
    assert r["explanation"] is None


async def test_option_breakdown_follows_show_answer(client, admin, course, make_user):
    step_id = await add_step(
        client,
        admin,
        course[1],
        multiple_choice(max_attempts=2, show_answer="after_attempts_exhausted"),
    )
    _, h = await make_user()
    first = (await submit(client, h, step_id, {"option_ids": [A]})).json()
    assert first["explanation"] is None  # an attempt is left: answer still hidden

    last = (await submit(client, h, step_id, {"option_ids": [A, B]})).json()
    marks = {
        o["id"]: (o["picked"], o["correct"]) for o in last["explanation"]["options"]
    }
    assert marks[A] == (True, True) and marks[B] == (True, True)

    # Once the answer is open, earlier submissions are explained too.
    mine = (await client.get(f"/steps/{step_id}/submissions", headers=h)).json()
    older = next(s for s in mine if s["id"] == first["id"])
    marks = {
        o["id"]: (o["picked"], o["correct"]) for o in older["explanation"]["options"]
    }
    assert marks[A] == (True, True) and marks[B] == (False, True)
    single = (await client.get(f"/submissions/{first['id']}", headers=h)).json()
    assert single["explanation"] == older["explanation"]


async def test_manual_review_creates_notification(
    client, admin, course, groups_setup, make_user
):
    step_id = await add_step(client, admin, course[1], free_text())
    (_, curator, _, student) = groups_setup[0]

    sub_id = (await submit(client, student, step_id, {"text": "essay"})).json()["id"]
    r = await client.post(
        f"/review/submissions/{sub_id}",
        json={"verdict": "accepted", "comment": "ok"},
        headers=curator,
    )
    assert r.status_code == 200, r.text

    listing = (await client.get("/notifications", headers=student)).json()
    assert len(listing) == 1
    n = listing[0]
    assert n["type"] == "submission_reviewed"
    assert n["severity"] == "success"
    assert n["read_at"] is None
    assert n["payload"] == {
        "submission_id": sub_id,
        "step_id": step_id,
        "course_id": course[0],
        "verdict": "accepted",
        "score": 5,
        "max_score": 5,
    }

    count = (await client.get("/notifications/unread_count", headers=student)).json()
    assert count == {"count": 1}

    r = await client.post(f"/notifications/{n['id']}/read", headers=student)
    assert r.status_code == 200 and r.json()["read_at"] is not None
    count = (await client.get("/notifications/unread_count", headers=student)).json()
    assert count == {"count": 0}

    _, other = await make_user()
    assert (await client.get("/notifications", headers=other)).json() == []


async def test_manual_review_rejected_severity(client, admin, course, groups_setup):
    step_id = await add_step(client, admin, course[1], free_text())
    (_, curator, _, student) = groups_setup[0]

    sub_id = (await submit(client, student, step_id, {"text": "essay"})).json()["id"]
    r = await client.post(
        f"/review/submissions/{sub_id}",
        json={"verdict": "rejected"},
        headers=curator,
    )
    assert r.status_code == 200, r.text

    n = (await client.get("/notifications", headers=student)).json()[0]
    assert n["severity"] == "warning"
    assert n["payload"]["verdict"] == "rejected"
    assert n["payload"]["score"] == 0


async def test_mark_all_read(client, admin, course, groups_setup):
    step_id = await add_step(client, admin, course[1], free_text())
    (_, curator, _, student) = groups_setup[0]
    sub_id = (await submit(client, student, step_id, {"text": "essay"})).json()["id"]
    await client.post(
        f"/review/submissions/{sub_id}",
        json={"verdict": "accepted"},
        headers=curator,
    )
    r = await client.post("/notifications/read_all", headers=student)
    assert r.json() == {"count": 0}
    unread = await client.get("/notifications?unread_only=true", headers=student)
    assert unread.json() == []


async def test_notification_dedup(client, make_user):
    from database import async_factory
    from notifications.models import NotificationType
    from notifications.payloads import HelloPayload
    from notifications.service import create_notification

    user_id, headers = await make_user()
    async with async_factory() as db:
        for _ in range(3):
            await create_notification(
                db,
                user_id,
                NotificationType.HELLO,
                HelloPayload(username="x"),
                dedup_key="hello:once",
            )
            await db.commit()

    r = await client.get("/notifications", headers=headers)
    assert len(r.json()) == 1


async def test_notification_payload_validated(client, make_user):
    from database import async_factory
    from notifications.models import NotificationType
    from notifications.service import create_notification

    user_id, _ = await make_user()
    async with async_factory() as db:
        with pytest.raises(ValueError):
            await create_notification(db, user_id, NotificationType.HELLO)
