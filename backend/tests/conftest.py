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

    async def run(self, code, cases, time_limit_s, memory_limit_kb, language="python3"):
        assert language == "python3", "LocalJudge runs Python only"
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
            try:
                out, err = await asyncio.wait_for(
                    proc.communicate(stdin.encode()), timeout=time_limit_s
                )
            except TimeoutError:
                # Like Judge0: an endless loop is stopped by the time limit.
                proc.kill()
                await proc.wait()
                results.append(RunResult("time_limit", None, None, time_limit_s))
                continue
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


@pytest_asyncio.fixture
async def admin(make_user):
    return await make_user("admin")


@pytest_asyncio.fixture
async def course(client, admin):
    """Published course with one module; returns (course_id, module_id)."""
    _, h = admin
    r = await client.post(
        "/admin/courses", json={"slug": "py", "title": "Python"}, headers=h
    )
    assert r.status_code == 201, r.text
    course_id = r.json()["id"]
    r = await client.post(
        f"/admin/courses/{course_id}/modules", json={"title": "Intro"}, headers=h
    )
    module_id = r.json()["id"]
    r = await client.patch(
        f"/admin/courses/{course_id}", json={"is_published": True}, headers=h
    )
    assert r.json()["is_published"]
    return course_id, module_id


class FakeStorage:
    """In-memory stand-in for the S3 bucket."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.reads = 0

    async def object_size(self, key):
        data = self.objects.get(key)
        return None if data is None else len(data)

    async def read_object(self, key):
        self.reads += 1
        if key not in self.objects:
            raise FileNotFoundError(key)
        return self.objects[key]


@pytest.fixture
def fake_storage(monkeypatch):
    from files import storage

    fake = FakeStorage()
    monkeypatch.setattr(storage, "object_size", fake.object_size)
    monkeypatch.setattr(storage, "read_object", fake.read_object)
    return fake


@pytest.fixture
def upload(client, fake_storage):
    """Upload bytes through the API as the given user; returns the file id."""

    async def do(
        headers, data: bytes, purpose="answer_key", complete=True, mime="text/plain"
    ):
        r = await client.post(
            "/files",
            json={
                "filename": "test.txt",
                "mime": mime,
                "size": len(data),
                "purpose": purpose,
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        # Presigned URL path: /<bucket>/<key>
        key = httpx.URL(r.json()["upload_url"]).path.split("/", 2)[2]
        fake_storage.objects[key] = data
        if complete:
            r2 = await client.post(f"/files/{r.json()['id']}/complete", headers=headers)
            assert r2.status_code == 200, r2.text
        return r.json()["id"]

    return do


@pytest_asyncio.fixture
async def groups_setup(client, admin, make_user):
    """Two groups, each with its own curator and student."""
    out = []
    for i in range(2):
        curator_id, curator_h = await make_user("curator")
        student_id, student_h = await make_user("student")
        r = await client.post(
            "/admin/groups",
            json={"name": f"G{i}", "curator_id": curator_id},
            headers=admin[1],
        )
        group_id = r.json()["id"]
        r = await client.put(
            f"/admin/groups/{group_id}/students/{student_id}", headers=admin[1]
        )
        assert r.status_code == 204
        out.append((group_id, curator_h, student_id, student_h))
    return out
