"""Test setup.

API tests need a disposable Postgres database, passed via TEST_DB_URL, e.g.
postgresql+asyncpg://postgres:postgres@localhost:5432/app_test
The schema is recreated from the models; all tables are truncated per test.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

TEST_DB_URL = os.environ.get("TEST_DB_URL")
if TEST_DB_URL:
    os.environ["DB_URL"] = TEST_DB_URL

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402

import all_models  # noqa: E402
from judge import RunResult  # noqa: E402


class LocalJudge:
    """Judge0 stand-in: runs the code with the local Python interpreter."""

    def __init__(self):
        self.calls = 0

    async def run(self, code, cases, time_limit_s, memory_limit_kb):
        self.calls += 1
        results = []
        for stdin, expected in cases:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                code,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate(stdin.encode())
            stdout = out.decode().replace("\r\n", "\n")
            if proc.returncode:
                verdict = "runtime_error"
            elif stdout.strip() == expected.strip():
                verdict = "ok"
            else:
                verdict = "wrong_answer"
            results.append(RunResult(verdict, stdout, err.decode(), 0.01))
        return results


@pytest.fixture
def local_judge():
    return LocalJudge()


requires_db = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DB_URL is not set")


@pytest_asyncio.fixture(scope="session")
async def _schema():
    from database import dbengine

    async with dbengine.begin() as conn:
        await conn.run_sync(all_models.metadata.drop_all)
        await conn.run_sync(all_models.metadata.create_all)
    yield
    await dbengine.dispose()


@pytest_asyncio.fixture
async def db_clean(_schema):
    from database import dbengine

    tables = ", ".join(t.name for t in all_models.metadata.sorted_tables)
    async with dbengine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def client(db_clean):
    from server import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api") as c:
        yield c


@pytest_asyncio.fixture
async def make_user(db_clean):
    """Create a user with a role; returns (user_id, auth headers)."""
    from auth import create_token, hasher
    from database import async_factory
    from models import Role, User

    counter = 0

    async def make(role: str = "student", username: str | None = None):
        nonlocal counter
        counter += 1
        name = username or f"{role}{counter:03d}"
        async with async_factory() as db:
            user = User(
                username=name,
                email=f"{name}@example.com",
                password=hasher.hash("password123"),
                role=Role(role),
            )
            db.add(user)
            await db.commit()
            token = create_token(user, "access")
            return user.id, {"Authorization": f"Bearer {token}"}

    return make
