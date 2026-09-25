"""The solution set in samples/verdicts gets exactly its expected verdicts.

Runs scripts/check_verdicts.py against the app in-process, with the judge
worker running in the background (LocalJudge instead of Judge0). On a real
stand the same script checks Judge0 itself.
"""

import asyncio
import sys
from pathlib import Path

from conftest import LocalJudge, requires_db

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_verdicts  # noqa: E402

pytestmark = requires_db


async def test_solution_set_verdicts(client, make_user, monkeypatch):
    import worker

    _, admin = await make_user("admin", username="verdictadmin")
    monkeypatch.setattr(worker, "IDLE_SLEEP", 0.05)
    stop = asyncio.Event()
    loop = asyncio.create_task(worker.run_loop(LocalJudge(), stop))
    try:
        checks = await check_verdicts.run(
            client, "verdictadmin", "password123", timeout=60
        )
    finally:
        stop.set()
        await asyncio.wait_for(loop, timeout=30)

    report = check_verdicts.report(checks)
    assert [c.file for c in checks] == [
        "wrong_answer.py",
        "runtime_error.py",
        "time_limit.py",
        "partial.py",
        "correct.py",
    ]
    assert all(c.ok for c in checks), report
    print(report)

    # The temporary course is removed afterwards.
    courses = (await client.get("/admin/courses", headers=admin)).json()
    assert not [c for c in courses if c["slug"].startswith("verdicts-")]
