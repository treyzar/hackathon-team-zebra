"""Minimal async client for Judge0 (https://judge0.com)."""

import asyncio
import base64
from dataclasses import dataclass

import httpx

from config import settings

# Judge0 status ids -> our verdicts.
_VERDICTS = {
    3: "ok",
    4: "wrong_answer",
    5: "time_limit",
    6: "compilation_error",
    **{i: "runtime_error" for i in range(7, 13)},
}
_PENDING = {1, 2}  # In Queue, Processing
BATCH_SIZE = 20  # Judge0 default MAX_SUBMISSION_BATCH_SIZE


class JudgeError(Exception):
    """Judge is unavailable or failed internally; the run should be retried."""


@dataclass
class RunResult:
    verdict: str
    stdout: str | None = None
    stderr: str | None = None
    time: float | None = None
    memory_kb: int | None = None


def _b64(s: str | None) -> str | None:
    return None if s is None else base64.b64encode(s.encode()).decode()


def _unb64(s: str | None) -> str | None:
    return None if s is None else base64.b64decode(s).decode(errors="replace")


class JudgeClient:
    def __init__(
        self,
        base_url: str = settings.judge0_url,
        auth_token: str | None = settings.judge0_auth_token,
        language_id: int = settings.judge0_python_language_id,
        poll_interval: float = 0.5,
        timeout: float = 120,
    ):
        headers = {"X-Auth-Token": auth_token} if auth_token else {}
        self._http = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30)
        self._language_id = language_id
        self._poll_interval = poll_interval
        self._timeout = timeout

    async def aclose(self) -> None:
        await self._http.aclose()

    async def run(
        self,
        code: str,
        cases: list[tuple[str, str]],
        time_limit_s: float,
        memory_limit_kb: int,
    ) -> list[RunResult]:
        """Run ``code`` on every (stdin, expected_stdout) case."""
        results: list[RunResult] = []
        for i in range(0, len(cases), BATCH_SIZE):
            chunk = cases[i : i + BATCH_SIZE]
            results += await self._run_batch(code, chunk, time_limit_s, memory_limit_kb)
        return results

    async def _run_batch(self, code, cases, time_limit_s, memory_limit_kb):
        body = {
            "submissions": [
                {
                    "language_id": self._language_id,
                    "source_code": _b64(code),
                    "stdin": _b64(stdin),
                    "expected_output": _b64(expected),
                    "cpu_time_limit": time_limit_s,
                    "memory_limit": memory_limit_kb,
                }
                for stdin, expected in cases
            ]
        }
        try:
            resp = await self._http.post(
                "/submissions/batch", params={"base64_encoded": "true"}, json=body
            )
            resp.raise_for_status()
            tokens = [item["token"] for item in resp.json()]
            return await self._wait(tokens)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as e:
            raise JudgeError(str(e)) from e

    async def _wait(self, tokens: list[str]) -> list[RunResult]:
        params = {
            "tokens": ",".join(tokens),
            "base64_encoded": "true",
            "fields": "token,status,stdout,stderr,compile_output,time,memory",
        }
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout
        while True:
            resp = await self._http.get("/submissions/batch", params=params)
            resp.raise_for_status()
            items = resp.json()["submissions"]
            if all(it["status"]["id"] not in _PENDING for it in items):
                return [self._to_result(it) for it in items]
            if loop.time() > deadline:
                raise JudgeError("Timed out waiting for the judge")
            await asyncio.sleep(self._poll_interval)

    @staticmethod
    def _to_result(item: dict) -> RunResult:
        status_id = item["status"]["id"]
        if status_id not in _VERDICTS:  # 13 Internal Error, 14 Exec Format Error
            raise JudgeError(f"Judge failure: {item['status'].get('description')}")
        return RunResult(
            verdict=_VERDICTS[status_id],
            stdout=_unb64(item.get("stdout")),
            stderr=_unb64(item.get("stderr") or item.get("compile_output")),
            time=float(item["time"]) if item.get("time") else None,
            memory_kb=item.get("memory"),
        )
