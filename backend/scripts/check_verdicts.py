"""Send a set of solutions with known verdicts to a running platform and check
that automatic grading gives exactly those verdicts.

It checks the whole chain for real: API -> queue -> worker -> Judge0 -> verdict.
A temporary course with the task is created (and deleted at the end), and a
temporary student is signed up and enrolled in it; an admin account is
required.

    cd backend
    ADMIN_PASSWORD=... uv run python scripts/check_verdicts.py \\
        --api https://cifrovye-zodchie.ru/api --admin <admin username>

Exit code 0 when every verdict matches, 1 otherwise.
"""

import argparse
import asyncio
import getpass
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

DEFAULT_SET = Path(__file__).resolve().parents[2] / "samples" / "verdicts" / "desks"
FINAL = {"correct", "partial", "wrong", "error"}


@dataclass
class Check:
    file: str
    expected: dict
    got: dict

    @property
    def ok(self) -> bool:
        return all(
            self.got.get(k) == v for k, v in self.expected.items() if k != "file"
        )


def first_failure(details: dict) -> tuple[str, dict | None]:
    """The first failing hidden test: (verdict, {group, test}), or ("ok", None)."""
    for group in details.get("groups", []):
        for i, test in enumerate(group["tests"], 1):
            if test["verdict"] != "ok":
                return test["verdict"], {"group": group["name"], "test": i}
    return "ok", None


async def login(client: httpx.AsyncClient, username: str, password: str) -> dict:
    r = await client.post(
        "/auth/login", json={"username": username, "password": password}
    )
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def signup_student(client: httpx.AsyncClient) -> dict:
    name = f"verdicts_{secrets.token_hex(4)}"
    r = await client.post(
        "/auth/signup",
        json={
            "email": f"{name}@example.com",
            "username": name,
            "password": secrets.token_urlsafe(16),
            "name": "Проверка",
            "surname": "Вердиктов",
        },
    )
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def wait_for_verdict(
    client: httpx.AsyncClient, headers: dict, submission_id: int, timeout: float
) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        r = await client.get(f"/submissions/{submission_id}", headers=headers)
        r.raise_for_status()
        sub = r.json()
        if sub["status"] in FINAL:
            return sub
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"No verdict for submission {submission_id} in {timeout}s"
            )
        await asyncio.sleep(1)


async def run(
    client: httpx.AsyncClient,
    admin: str,
    password: str,
    set_dir: Path = DEFAULT_SET,
    timeout: float = 180,
    keep: bool = False,
) -> list[Check]:
    task = json.loads((set_dir / "task.json").read_text(encoding="utf-8"))
    expected = json.loads((set_dir / "expected.json").read_text(encoding="utf-8"))
    admin_h = await login(client, admin, password)

    r = await client.post(
        "/admin/courses",
        json={
            "slug": f"verdicts-{secrets.token_hex(4)}",
            "title": "Проверка вердиктов",
        },
        headers=admin_h,
    )
    r.raise_for_status()
    course_id = r.json()["id"]
    try:
        r = await client.post(
            f"/admin/courses/{course_id}/modules",
            json={"title": "Задача"},
            headers=admin_h,
        )
        r.raise_for_status()
        r = await client.post(
            f"/admin/modules/{r.json()['id']}/steps",
            json={"payload": task},
            headers=admin_h,
        )
        r.raise_for_status()
        step_id = r.json()["id"]
        r = await client.patch(
            f"/admin/courses/{course_id}", json={"is_published": True}, headers=admin_h
        )
        r.raise_for_status()

        student_h = await signup_student(client)
        me = await client.get("/user/me", headers=student_h)
        me.raise_for_status()
        # Students see only the courses they are enrolled in.
        r = await client.post(
            f"/admin/courses/{course_id}/enrollments",
            json={"user_ids": [me.json()["id"]]},
            headers=admin_h,
        )
        r.raise_for_status()
        checks = []
        # One at a time: a new submission is refused while one is being checked.
        for exp in expected:
            code = (set_dir / "solutions" / exp["file"]).read_text(encoding="utf-8")
            r = await client.post(
                f"/steps/{step_id}/submissions",
                json={"answer": {"code": code}},
                headers=student_h,
            )
            r.raise_for_status()
            sub = await wait_for_verdict(client, student_h, r.json()["id"], timeout)
            verdict, failed_at = first_failure(sub["result_details"])
            got = {
                "status": sub["status"],
                "score": sub["score"],
                "verdict": verdict,
                "failed_at": failed_at,
            }
            checks.append(Check(exp["file"], exp, got))
        return checks
    finally:
        if not keep:
            await client.delete(f"/admin/courses/{course_id}", headers=admin_h)


def describe(result: dict) -> str:
    where = result.get("failed_at")
    place = f", группа «{where['group']}», тест {where['test']}" if where else ""
    return f"{result['status']}, {result['score']} б., {result['verdict']}{place}"


def report(checks: list[Check]) -> str:
    lines = []
    for c in checks:
        mark = "OK  " if c.ok else "FAIL"
        lines.append(f"{mark} {c.file}")
        lines.append(f"     ожидали:  {describe(c.expected)}")
        if not c.ok:
            lines.append(f"     получили: {describe(c.got)}")
    passed = sum(c.ok for c in checks)
    lines.append(f"\nСовпало {passed} из {len(checks)}")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--api", required=True, help="e.g. https://cifrovye-zodchie.ru/api"
    )
    parser.add_argument("--admin", required=True, help="admin username")
    parser.add_argument(
        "--set", type=Path, default=DEFAULT_SET, help="solution set dir"
    )
    parser.add_argument(
        "--timeout", type=float, default=180, help="seconds per verdict"
    )
    parser.add_argument("--keep", action="store_true", help="keep the temporary course")
    args = parser.parse_args()
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")

    async with httpx.AsyncClient(base_url=args.api, timeout=30) as client:
        checks = await run(
            client, args.admin, password, args.set, args.timeout, args.keep
        )
    print(report(checks))
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
