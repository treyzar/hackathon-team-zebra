"""Judge worker and file-based programming tests (needs TEST_DB_URL)."""

import asyncio
from datetime import timedelta

import pytest
from conftest import LocalJudge, requires_db
from test_api import add_step, programming, submit

pytestmark = requires_db

SQUARE = "print(int(input()) ** 2)"


async def get_sub(sub_id):
    from database import async_factory
    from submissions.models import Submission

    async with async_factory() as db:
        return await db.get(Submission, sub_id)


async def set_sub(sub_id, **values):
    from sqlalchemy import update

    from database import async_factory
    from submissions.models import Submission

    async with async_factory() as db, db.begin():
        await db.execute(
            update(Submission).where(Submission.id == sub_id).values(**values)
        )


def reader():
    """Fresh cache per test: ids restart after each TRUNCATE."""
    from database import async_factory
    from files.reader import CachedFileReader

    return CachedFileReader(async_factory, 10 * 2**20)


async def drain(judge, files=None):
    """Run the worker until the queue is empty."""
    import worker

    files = files or reader()
    while (sub_id := await worker.claim_next()) is not None:
        await worker.process(sub_id, judge, files)


@pytest.fixture
async def queued(client, admin, course, make_user):
    """A student's programming submission waiting in the queue."""
    step_id = await add_step(client, admin, course[1], programming())
    _, h = await make_user()
    r = await submit(client, h, step_id, {"code": SQUARE})
    assert r.json()["status"] == "queued"
    return r.json()["id"]


class FlakyJudge(LocalJudge):
    """Fails the first ``failures`` calls with a JudgeError."""

    def __init__(self, failures=1):
        super().__init__()
        self.failures = failures

    async def run(self, *args, **kwargs):
        from judge import JudgeError

        if self.failures:
            self.failures -= 1
            raise JudgeError("judge restarting")
        return await super().run(*args, **kwargs)


# --- queue mechanics -------------------------------------------------------


async def test_claim_on_empty_queue(db_clean):
    import worker

    assert await worker.claim_next() is None


async def test_claim_marks_running(queued):
    import worker

    assert await worker.claim_next() == queued
    sub = await get_sub(queued)
    assert (sub.status, sub.judge_attempts) == ("running", 1)
    assert sub.judge_started_at is not None
    assert await worker.claim_next() is None  # nobody else gets it


async def test_stale_running_is_requeued(queued):
    import worker
    from config import settings
    from courses.service import now

    await worker.claim_next()
    old = now() - timedelta(seconds=settings.judge_stale_after_seconds + 1)
    await set_sub(queued, judge_started_at=old)
    assert await worker.claim_next() == queued
    assert (await get_sub(queued)).judge_attempts == 2


async def test_gives_up_after_max_retries(queued):
    import worker
    from config import settings

    await set_sub(queued, judge_attempts=settings.judge_max_retries)
    assert await worker.claim_next() is None
    sub = await get_sub(queued)
    assert sub.status == "error"
    assert "Gave up" in sub.judge_error


# --- outcomes of a run -----------------------------------------------------


async def test_judge_error_is_retried(queued):
    judge = FlakyJudge(failures=1)
    await drain(judge)
    sub = await get_sub(queued)
    assert (sub.status, sub.score, sub.judge_attempts) == ("correct", 10, 2)


async def test_judge_error_until_retries_run_out(queued):
    from config import settings

    await drain(FlakyJudge(failures=100))
    sub = await get_sub(queued)
    assert sub.status == "error"
    assert sub.judge_attempts == settings.judge_max_retries
    assert sub.judge_error == "judge restarting"


async def test_language_missing_in_judge0_is_final(queued):
    from judge import LanguageUnavailableError

    class NoLanguage:
        async def run(self, *args, **kwargs):
            raise LanguageUnavailableError("Judge0 has no language 'python3'")

    await drain(NoLanguage())
    sub = await get_sub(queued)
    # A repeat run would fail the same way: no retries.
    assert (sub.status, sub.judge_attempts) == ("error", 1)
    assert "no language" in sub.judge_error


async def test_unexpected_error_is_final(queued):
    class Broken:
        async def run(self, *args, **kwargs):
            raise RuntimeError("bug")

    await drain(Broken())
    sub = await get_sub(queued)
    assert (sub.status, sub.judge_attempts) == ("error", 1)
    assert sub.judge_error == "Internal error: bug"


async def test_result_dropped_if_requeued_meanwhile(queued):
    """If the run took so long that it was requeued as stale, the late result
    must not overwrite the state another worker now owns."""
    import worker

    class Slow(LocalJudge):
        async def run(self, *args, **kwargs):
            await set_sub(queued, status="queued")
            return await super().run(*args, **kwargs)

    sub_id = await worker.claim_next()
    await worker.process(sub_id, Slow(), reader())
    sub = await get_sub(queued)
    assert (sub.status, sub.score) == ("queued", None)


# --- loop and shutdown -----------------------------------------------------


async def test_run_loop_processes_and_stops(queued, monkeypatch):
    import worker

    monkeypatch.setattr(worker, "IDLE_SLEEP", 0.05)
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run_loop(LocalJudge(), stop))
    for _ in range(200):
        if (await get_sub(queued)).status not in ("queued", "running"):
            break
        await asyncio.sleep(0.05)
    assert (await get_sub(queued)).status == "correct"
    stop.set()
    await asyncio.wait_for(task, timeout=2)  # wakes up from idle at once


async def test_run_loop_survives_claim_failure(db_clean, monkeypatch):
    import worker

    calls = 0

    async def failing_claim():
        nonlocal calls
        calls += 1
        raise ConnectionError("db down")

    monkeypatch.setattr(worker, "claim_next", failing_claim)
    monkeypatch.setattr(worker, "IDLE_SLEEP", 0.01)
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run_loop(LocalJudge(), stop))
    await asyncio.sleep(0.1)
    stop.set()
    await asyncio.wait_for(task, timeout=2)
    assert calls > 1  # kept trying instead of crashing


async def test_main_stops_and_keeps_injected_judge_open(db_clean):
    import worker

    class Judge(LocalJudge):
        closed = False

        async def aclose(self):
            self.closed = True

    judge, stop = Judge(), asyncio.Event()
    stop.set()
    await asyncio.wait_for(worker.main(concurrency=2, judge=judge, stop=stop), 5)
    assert not judge.closed


# --- large tests stored as files -------------------------------------------


def file_step(input_file, output_file, grading="tests"):
    step = programming(grading=grading, scoring="per_group")
    step["answer_key"]["test_groups"].append(
        {
            "name": "big",
            "points": 5,
            "tests": [{"input_file": input_file, "output_file": output_file}],
        }
    )
    step["max_score"] = 15
    return step


async def test_answer_key_files_are_private(client, admin, make_user, upload):
    _, student = await make_user()
    _, curator = await make_user("curator")
    req = {
        "filename": "t.txt",
        "mime": "text/plain",
        "size": 1,
        "purpose": "answer_key",
    }
    assert (await client.post("/files", json=req, headers=student)).status_code == 403
    assert (await client.post("/files", json=req, headers=curator)).status_code == 403

    file_id = await upload(admin[1], b"secret test")
    assert (await client.get(f"/files/{file_id}", headers=student)).status_code == 404
    assert (await client.get(f"/files/{file_id}", headers=curator)).status_code == 200
    assert (await client.get(f"/files/{file_id}", headers=admin[1])).status_code == 200


async def test_large_tests_from_storage(
    client, admin, course, make_user, upload, fake_storage
):
    big_input = "\n".join(str(i) for i in range(20_000)) + "\n"
    expected = str(sum(range(20_000))) + "\n"
    inp = await upload(admin[1], big_input.encode())
    out = await upload(admin[1], expected.encode())
    step_id = await add_step(client, admin, course[1], file_step(inp, out))

    # Hidden tests stay hidden: the student view has no file ids.
    _, h = await make_user()
    view = (await client.get(f"/steps/{step_id}", headers=h)).json()
    assert str(inp) not in str(view["content"])

    code = (
        "import sys\n"
        "data = sys.stdin.read().split()\n"
        "print(sum(map(int, data)) if len(data) > 1 else int(data[0]) ** 2)"
    )
    files = reader()
    r1 = (await submit(client, h, step_id, {"code": code})).json()
    await drain(LocalJudge(), files)
    # A full score closes the step for this student, so a second one submits.
    _, h2 = await make_user()
    r2 = (await submit(client, h2, step_id, {"code": code})).json()
    await drain(LocalJudge(), files)

    for sub_id in (r1["id"], r2["id"]):
        sub = await get_sub(sub_id)
        assert (sub.status, sub.score) == ("correct", 15), sub.result_details
        assert sub.result_details["groups"][2]["passed"]
    # Two submissions, two files: each downloaded once thanks to the cache.
    assert fake_storage.reads == 2


@pytest.mark.parametrize("problem", ["content_purpose", "unknown", "not_uploaded"])
async def test_step_rejects_bad_test_files(client, admin, course, upload, problem):
    good = await upload(admin[1], b"1\n")
    bad = {
        "content_purpose": lambda: upload(admin[1], b"1\n", purpose="content"),
        "not_uploaded": lambda: upload(admin[1], b"1\n", complete=False),
    }
    bad_id = 999_999 if problem == "unknown" else await bad[problem]()
    r = await client.post(
        f"/admin/modules/{course[1]}/steps",
        json={"payload": file_step(good, bad_id)},
        headers=admin[1],
    )
    assert r.status_code == 422, r.text


async def test_storage_failure_is_retried(client, admin, course, make_user, upload):
    from config import settings
    from files.storage import StorageError

    inp = await upload(admin[1], b"3\n")
    out = await upload(admin[1], b"9\n")
    step_id = await add_step(client, admin, course[1], file_step(inp, out))
    _, h = await make_user()
    sub_id = (await submit(client, h, step_id, {"code": SQUARE})).json()["id"]

    class DownStorage:
        async def text(self, file_id):
            raise StorageError("s3 unavailable")

    await drain(LocalJudge(), DownStorage())
    sub = await get_sub(sub_id)
    assert (sub.status, sub.judge_attempts) == ("error", settings.judge_max_retries)
    assert sub.judge_error == "s3 unavailable"
