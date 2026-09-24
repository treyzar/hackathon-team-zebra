"""Judge worker: takes queued submissions from Postgres and runs their tests.

Postgres is the queue (SELECT ... FOR UPDATE SKIP LOCKED), so several workers
can run side by side. Run from backend/src: python worker.py
"""

import asyncio
import logging
import signal
from datetime import timedelta
from functools import partial

from sqlalchemy import select, update

import all_models  # noqa: F401  # register every mapper
from config import settings
from courses.models import Step, StepRevision
from courses.service import now, parse
from database import async_factory, dbengine
from files.reader import CachedFileReader
from files.storage import StorageError
from judge import JudgeClient, JudgeError
from steps.base import TestFiles
from submissions.models import Submission, SubmissionStatus
from submissions.service import apply_auto_result

log = logging.getLogger("worker")
IDLE_SLEEP = 1.0
# Temporary infrastructure failures: the run is retried.
RETRYABLE = (JudgeError, StorageError)

# Shared by all loops of the process, so test files are downloaded once.
file_reader = CachedFileReader(
    async_factory, settings.worker_file_cache_mb * 1024 * 1024
)


async def claim_next() -> int | None:
    async with async_factory() as db, db.begin():
        # A worker died mid-run: give the submission back to the queue.
        stale = now() - timedelta(seconds=settings.judge_stale_after_seconds)
        await db.execute(
            update(Submission)
            .where(
                Submission.status == SubmissionStatus.RUNNING,
                Submission.judge_started_at < stale,
            )
            .values(status=SubmissionStatus.QUEUED)
        )
        sub = await db.scalar(
            select(Submission)
            .where(Submission.status == SubmissionStatus.QUEUED)
            .order_by(Submission.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not sub:
            return None
        if sub.judge_attempts >= settings.judge_max_retries:
            sub.status = SubmissionStatus.ERROR
            sub.judge_error = sub.judge_error or "Gave up after retries"
            return None
        sub.status = SubmissionStatus.RUNNING
        sub.judge_started_at = now()
        sub.judge_attempts += 1
        return sub.id


async def _finish(sub_id: int, apply) -> None:
    async with async_factory() as db, db.begin():
        sub = await db.get(Submission, sub_id, with_for_update=True)
        # Requeued as stale meanwhile: another worker owns it now.
        if sub and sub.status == SubmissionStatus.RUNNING:
            apply(sub)


def _fail(sub: Submission, message: str, retry: bool = False) -> None:
    """Judge failures are retried a few times; other errors are final."""
    sub.judge_error = message[:1000]
    if retry and sub.judge_attempts < settings.judge_max_retries:
        sub.status = SubmissionStatus.QUEUED
    else:
        sub.status = SubmissionStatus.ERROR


async def process(
    sub_id: int, judge: JudgeClient, files: TestFiles = file_reader
) -> None:
    async with async_factory() as db:
        sub = await db.get(Submission, sub_id)
        rev = await db.get(StepRevision, sub.step_revision_id)
        step = await db.get(Step, sub.step_id)
        parsed = parse(step, rev)
        answer = parsed.type.answer_model.model_validate(sub.answer)
    # The DB connection is released while the judge runs.
    try:
        result = await parsed.type.run_tests(
            judge,
            files,
            parsed.content,
            parsed.answer_key,
            parsed.settings,
            answer,
            parsed.max_score,
        )
    except RETRYABLE as e:
        log.warning("submission %s: judge error: %s", sub_id, e)
        await _finish(sub_id, partial(_fail, message=str(e), retry=True))
        return
    except Exception as e:
        log.exception("submission %s: grading crashed", sub_id)
        await _finish(sub_id, partial(_fail, message=f"Internal error: {e}"))
        return

    await _finish(
        sub_id,
        lambda s: apply_auto_result(
            s, parsed.settings.grading, result, parsed.max_score
        ),
    )
    log.info("submission %s: score %s", sub_id, result.score)


async def run_loop(judge: JudgeClient, stop: asyncio.Event) -> None:
    """Process submissions until ``stop`` is set; the current one is finished."""
    while not stop.is_set():
        try:
            sub_id = await claim_next()
        except Exception:
            log.exception("failed to claim a submission")
            sub_id = None
        if sub_id is None:
            # Idle: wait for new work, but wake up at once on stop.
            try:
                await asyncio.wait_for(stop.wait(), IDLE_SLEEP)
            except TimeoutError:
                pass
            continue
        await process(sub_id, judge)


def _stop_on_signals(stop: asyncio.Event) -> None:
    """docker stop sends SIGTERM: finish running checks, then exit."""
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError):  # Windows
            pass


async def main(
    concurrency: int = settings.worker_concurrency,
    judge: JudgeClient | None = None,
    stop: asyncio.Event | None = None,
) -> None:
    own_judge = judge is None
    judge = judge or JudgeClient()
    stop = stop or asyncio.Event()
    _stop_on_signals(stop)
    log.info("worker started, concurrency=%s", concurrency)
    try:
        await asyncio.gather(*(run_loop(judge, stop) for _ in range(concurrency)))
    finally:
        if own_judge:
            await judge.aclose()
        await dbengine.dispose()
    log.info("worker stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    asyncio.run(main())
