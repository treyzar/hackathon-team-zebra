"""Skill map: module skills set by admins, states computed from progress."""

from conftest import requires_db
from test_access import make_sequential
from test_api import DOC, A, B, add_step, free_text, single_choice, submit

pytestmark = requires_db
THEORY = {"type": "theory", "content": {"body": DOC}}


async def add_module(client, admin, course_id, title, skills):
    r = await client.post(
        f"/admin/courses/{course_id}/modules",
        json={"title": title, "skills": skills},
        headers=admin[1],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def tree_skills(client, admin, course_id):
    tree = (await client.get(f"/admin/courses/{course_id}", headers=admin[1])).json()
    return {m["title"]: m["skills"] for m in tree["modules"]}


async def skill_map(client, headers):
    r = await client.get("/skills", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def states(course):
    return {s["name"]: s["state"] for s in course["skills"]}


# --- authoring ---------------------------------------------------------------


async def test_module_skills_are_cleaned_and_kept(client, admin, course):
    module = await add_module(
        client, admin, course[0], "Циклы", ["  Циклы  for ", "циклы for", "", "Условия"]
    )
    assert (await tree_skills(client, admin, course[0]))["Циклы"] == [
        "Циклы for",
        "Условия",
    ]
    # Renaming keeps the skills; setting skills keeps the name.
    url = f"/admin/modules/{module}"
    await client.patch(url, json={"title": "Повторение"}, headers=admin[1])
    assert (await tree_skills(client, admin, course[0]))["Повторение"] == [
        "Циклы for",
        "Условия",
    ]
    await client.patch(url, json={"skills": ["Списки"]}, headers=admin[1])
    assert (await tree_skills(client, admin, course[0]))["Повторение"] == ["Списки"]

    for bad in ({"skills": ["x" * 61]}, {"skills": [f"s{i}" for i in range(13)]}):
        assert (await client.patch(url, json=bad, headers=admin[1])).status_code == 422


async def test_export_and_import_keep_skills(client, admin, course):
    await add_module(client, admin, course[0], "Циклы", ["Циклы", "Условия"])
    exported = await client.get(f"/admin/courses/{course[0]}/export", headers=admin[1])
    modules = exported.json()["course"]["modules"]
    assert [m["skills"] for m in modules] == [[], ["Циклы", "Условия"]]
    r = await client.post(
        "/admin/courses/import",
        files={"file": ("c.json", exported.content, "application/json")},
        headers=admin[1],
    )
    copy = await tree_skills(client, admin, r.json()["course_id"])
    assert copy["Циклы"] == ["Циклы", "Условия"]


# --- the map -------------------------------------------------------------------


async def test_states_open_done_gold(client, admin, course, make_user):
    basics = await add_module(client, admin, course[0], "Основы", ["Ввод", "Вывод"])
    loops = await add_module(client, admin, course[0], "Циклы", ["Циклы"])
    await add_module(client, admin, course[0], "Пусто", ["Ещё впереди"])
    await add_step(client, admin, course[1], single_choice())  # module without skills
    theory = await add_step(client, admin, basics, THEORY)
    choice = await add_step(client, admin, basics, single_choice())
    loop = await add_step(client, admin, loops, single_choice())

    _, fresh = await make_user()
    _, star = await make_user()
    [course_map] = await skill_map(client, fresh)
    assert course_map["title"] == "Python"
    # Only modules with skills, in course order; nothing earned yet.
    assert [(s["name"], s["state"]) for s in course_map["skills"]] == [
        ("Ввод", "open"),
        ("Вывод", "open"),
        ("Циклы", "open"),
        ("Ещё впереди", "open"),
    ]
    assert (
        course_map["skills"][0]["steps_completed"],
        course_map["skills"][0]["steps_total"],
    ) == (0, 2)

    await submit(client, star, theory, {})
    await submit(client, star, choice, {"option_id": A})  # first try, full score
    await submit(client, star, loop, {"option_id": B})  # wrong first
    [course_map] = await skill_map(client, star)
    assert states(course_map) == {
        "Ввод": "gold",
        "Вывод": "gold",
        "Циклы": "in_progress",
        "Ещё впереди": "open",  # no steps: nothing to earn
    }
    await submit(client, star, loop, {"option_id": A})  # solved, but not first
    assert states((await skill_map(client, star))[0])["Циклы"] == "done"


async def test_theory_alone_is_not_the_whole_module(client, admin, course, make_user):
    module = await add_module(client, admin, course[0], "Основы", ["Ввод"])
    theory = await add_step(client, admin, module, THEORY)
    await add_step(client, admin, module, single_choice())
    _, student = await make_user()
    await submit(client, student, theory, {})
    assert states((await skill_map(client, student))[0]) == {"Ввод": "in_progress"}


async def test_hidden_steps_do_not_count(client, admin, course, make_user):
    module = await add_module(client, admin, course[0], "Основы", ["Ввод"])
    step = await add_step(client, admin, module, single_choice())
    hidden = await add_step(client, admin, module, single_choice())
    await client.patch(
        f"/admin/steps/{hidden}", json={"is_hidden": True}, headers=admin[1]
    )
    _, student = await make_user()
    await submit(client, student, step, {"option_id": A})
    assert states((await skill_map(client, student))[0]) == {"Ввод": "gold"}


async def test_courses_on_the_map(client, admin, course, make_user):
    await add_module(client, admin, course[0], "Основы", ["Ввод"])
    draft = (
        await client.post(
            "/admin/courses",
            json={"slug": "draft", "title": "Черновик"},
            headers=admin[1],
        )
    ).json()["id"]
    await add_module(client, admin, draft, "M", ["Навык черновика"])
    student_id, student = await make_user()
    # Enrolled, but not published: not on the map.
    await client.post(
        f"/admin/courses/{draft}/enrollments",
        json={"user_ids": [student_id]},
        headers=admin[1],
    )
    assert [c["title"] for c in await skill_map(client, student)] == ["Python"]
    # Not enrolled: no map at all.
    _, outsider = await make_user(enroll=False)
    assert await skill_map(client, outsider) == []


async def test_only_students(client, make_user):
    _, curator = await make_user("curator")
    assert (await client.get("/skills", headers=curator)).status_code == 403


async def test_locked_modules_open_after_the_previous(client, admin, course, make_user):
    first = await add_module(client, admin, course[0], "Основы", ["Ввод"])
    second = await add_module(client, admin, course[0], "Циклы", ["Циклы"])
    step1 = await add_step(client, admin, first, single_choice())
    await add_step(client, admin, second, single_choice())
    _, student = await make_user()

    # Every step open: nothing is locked.
    assert states((await skill_map(client, student))[0]) == {
        "Ввод": "open",
        "Циклы": "open",
    }

    await make_sequential(client, admin, course)
    [course_map] = await skill_map(client, student)
    assert states(course_map) == {"Ввод": "open", "Циклы": "locked"}
    assert [s["opens_after"] for s in course_map["skills"]] == [None, "Основы"]
    assert course_map["skills"][1]["next_step_id"] is None

    await submit(client, student, step1, {"option_id": A})
    assert states((await skill_map(client, student))[0]) == {
        "Ввод": "gold",
        "Циклы": "open",
    }


async def test_counts_continue_and_you_are_here(client, admin, course, groups_setup):
    (_, curator, _, student), _ = groups_setup
    module = await add_module(client, admin, course[0], "Проекты", ["Проект"])
    done = await add_step(client, admin, module, single_choice())
    checking = await add_step(client, admin, module, free_text())
    returned = await add_step(client, admin, module, free_text())
    await add_step(client, admin, module, single_choice())  # ahead

    await submit(client, student, done, {"option_id": A})
    await submit(client, student, checking, {"text": "x"})
    sub = (await submit(client, student, returned, {"text": "x"})).json()["id"]
    await client.post(
        f"/review/submissions/{sub}", json={"verdict": "rejected"}, headers=curator
    )

    [skill] = (await skill_map(client, student))[0]["skills"]
    assert skill["state"] == "in_progress"
    assert (
        skill["steps_total"],
        skill["steps_completed"],
        skill["steps_checking"],
        skill["steps_returned"],
    ) == (4, 1, 1, 1)
    # "Continue" leads to the returned step: it waits for a new attempt.
    assert skill["next_step_id"] == returned
    assert skill["current"] is True


async def test_pdf_lists_module_skills():
    from types import SimpleNamespace

    from courses.pdf_export import _build_pdf_html

    course = SimpleNamespace(
        title="Python",
        slug="py",
        is_published=True,
        step_access=SimpleNamespace(value="all"),
        description=None,
    )
    modules = [
        SimpleNamespace(id=1, title="Циклы", skills=["Циклы for", "<Условия>"]),
        SimpleNamespace(id=2, title="Без навыков", skills=[]),
    ]
    html = _build_pdf_html(course, modules, {1: [], 2: []}, {}, True)
    assert "Навыки: Циклы for, &lt;Условия&gt;" in html
    assert html.count("Навыки:") == 1
