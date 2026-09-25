"""JudgeClient against an in-process fake of the Judge0 HTTP API."""

import base64
import json
import uuid

import httpx
import pytest

from judge import BATCH_SIZE, JudgeClient, JudgeError, LanguageUnavailableError


def b64(s):
    return None if s is None else base64.b64encode(s.encode()).decode()


def unb64(s):
    return None if s is None else base64.b64decode(s).decode()


# What GET /languages of Judge0 CE 1.13 returns for the languages we support.
LANGUAGES_113 = [
    {"id": 70, "name": "Python (2.7.17)"},
    {"id": 71, "name": "Python (3.8.1)"},
    {"id": 63, "name": "JavaScript (Node.js 12.14.0)"},
    {"id": 93, "name": "JavaScript (Node.js 18.15.0)"},
    {"id": 52, "name": "C++ (GCC 7.4.0)"},
    {"id": 54, "name": "C++ (GCC 9.2.0)"},
    {"id": 53, "name": "C++ (GCC 8.3.0)"},
    {"id": 76, "name": "C++ (Clang 7.0.1)"},
    {"id": 51, "name": "C# (Mono 6.6.0.161)"},
    {"id": 60, "name": "Go (1.13.5)"},
    {"id": 95, "name": "Go (1.18.5)"},
    {"id": 67, "name": "Pascal (FPC 3.0.4)"},
    {"id": 89, "name": "Multi-file program"},
]


class FakeJudge0:
    """Implements GET /languages and POST/GET /submissions/batch. What a
    submission "does" is chosen by its source code: echo, tle, crash,
    compile, internal."""

    def __init__(self, polls_before_done=1):
        self.languages = LANGUAGES_113
        self.languages_status = 200
        self.polls_before_done = polls_before_done
        self.pending_forever = False
        self.post_status = None  # force an HTTP error on POST
        self.batches = []  # decoded submissions, per POST
        self.requests = []
        self._results = {}
        self._polls = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/languages":
            if self.languages_status != 200:
                return httpx.Response(self.languages_status, json={"error": "nope"})
            return httpx.Response(200, json=self.languages)
        assert request.url.params["base64_encoded"] == "true"
        if request.method == "POST":
            if self.post_status:
                return httpx.Response(self.post_status, json={"error": "nope"})
            subs = json.loads(request.content)["submissions"]
            batch, tokens = [], []
            for sub in subs:
                sub = dict(sub)
                for k in ("source_code", "stdin", "expected_output"):
                    sub[k] = unb64(sub[k])
                batch.append(sub)
                token = str(uuid.uuid4())
                self._results[token] = self._run(token, sub)
                self._polls[token] = 0
                tokens.append({"token": token})
            self.batches.append(batch)
            return httpx.Response(201, json=tokens)

        items = []
        for token in request.url.params["tokens"].split(","):
            self._polls[token] += 1
            if self.pending_forever or self._polls[token] <= self.polls_before_done:
                items.append(
                    {"token": token, "status": {"id": 1, "description": "In Queue"}}
                )
            else:
                items.append(self._results[token])
        return httpx.Response(200, json={"submissions": items})

    @staticmethod
    def _run(token, sub):
        code, stdin, expected = sub["source_code"], sub["stdin"], sub["expected_output"]
        out, err, status = None, None, 3
        if code == "echo":
            out = stdin
            status = 3 if out.strip() == (expected or "").strip() else 4
        elif code == "tle":
            status = 5
        elif code == "crash":
            status, err = 11, "Traceback: ZeroDivisionError"
        elif code == "compile":
            status = 6
        elif code == "internal":
            status = 13
        return {
            "token": token,
            "status": {"id": status, "description": "..."},
            "stdout": b64(out),
            "stderr": b64(err),
            "compile_output": None,
            "time": "0.012",
            "memory": 3456,
        }


@pytest.fixture
def fake():
    return FakeJudge0()


def client(fake, **kw):
    kw.setdefault("auth_token", "secret")
    return JudgeClient(
        base_url="http://judge0",
        max_output_kb=2048,
        poll_interval=0,
        transport=httpx.MockTransport(fake.handler),
        **kw,
    )


async def test_results_in_order_and_decoded(fake):
    j = client(fake)
    runs = await j.run("echo", [("привет\n", "привет"), ("a", "b")], 1.5, 262144)
    await j.aclose()
    assert [r.verdict for r in runs] == ["ok", "wrong_answer"]
    assert runs[0].stdout == "привет\n"  # base64 round trip keeps unicode
    assert (runs[0].time, runs[0].memory_kb) == (0.012, 3456)


async def test_request_fields(fake):
    j = client(fake)
    await j.run("echo", [("1", "1")], 1.5, 262144)
    post = fake.requests[0]
    assert post.headers["X-Auth-Token"] == "secret"
    sub = fake.batches[0][0]
    assert sub["language_id"] == 71  # python3 by default: newest Python 3
    assert sub["cpu_time_limit"] == 1.5
    assert sub["memory_limit"] == 262144
    assert sub["max_file_size"] == 2048
    # Polling is authenticated too.
    assert all(r.headers["X-Auth-Token"] == "secret" for r in fake.requests)


@pytest.mark.parametrize(
    ("language", "language_id"),
    [
        ("python3", 71),
        ("javascript", 93),
        ("cpp", 54),
        ("csharp", 51),
        ("go", 95),
        ("pascal", 67),
    ],
)
async def test_language_is_looked_up_in_judge0(fake, language, language_id):
    await client(fake).run("echo", [("1", "1")], 1, 1024, language=language)
    assert {s["language_id"] for s in fake.batches[0]} == {language_id}


async def test_language_list_is_cached_then_refreshed(fake):
    j = client(fake, languages_ttl=3600)
    await j.run("echo", [("1", "1")], 1, 1024)
    await j.run("echo", [("1", "1")], 1, 1024)
    assert [r.url.path for r in fake.requests].count("/languages") == 1

    # Judge0 was upgraded: ids changed. Once the cache expires we follow.
    fake.languages = [{"id": 100, "name": "Python (3.12.5)"}]
    j = client(fake, languages_ttl=0)
    await j.run("echo", [("1", "1")], 1, 1024)
    assert fake.batches[-1][0]["language_id"] == 100


async def test_language_missing_in_judge0_is_not_retryable(fake):
    fake.languages = [{"id": 100, "name": "Python (3.12.5)"}]
    with pytest.raises(LanguageUnavailableError, match="go"):
        await client(fake).run("echo", [("1", "1")], 1, 1024, language="go")
    assert not fake.batches  # nothing was sent


async def test_language_list_failure_is_a_judge_error(fake):
    fake.languages_status = 503
    with pytest.raises(JudgeError):
        await client(fake).run("echo", [("1", "1")], 1, 1024)


async def test_stale_language_list_is_used_when_refresh_fails(fake):
    j = client(fake, languages_ttl=0)
    await j.run("echo", [("1", "1")], 1, 1024)
    fake.languages_status = 503
    runs = await j.run("echo", [("1", "1")], 1, 1024)
    assert runs[0].verdict == "ok"


async def test_no_auth_header_without_token(fake):
    j = client(fake, auth_token=None)
    await j.run("echo", [("1", "1")], 1, 1024)
    assert "X-Auth-Token" not in fake.requests[0].headers


async def test_batches_by_count_keep_order(fake):
    cases = [(str(i), str(i)) for i in range(2 * BATCH_SIZE + 5)]
    runs = await client(fake).run("echo", cases, 1, 1024)
    assert [len(b) for b in fake.batches] == [BATCH_SIZE, BATCH_SIZE, 5]
    assert [r.stdout for r in runs] == [c[0] for c in cases]


async def test_batches_by_size(fake):
    j = client(fake, batch_max_bytes=100)
    cases = [("x" * 30, "x" * 30)] * 3 + [("y" * 500, "y" * 500), ("z", "z")]
    runs = await j.run("echo", cases, 1, 1024)
    # 60 bytes each: one per batch; an oversized case goes alone.
    assert [len(b) for b in fake.batches] == [1, 1, 1, 1, 1]
    assert all(r.verdict == "ok" for r in runs)


async def test_polls_until_done():
    fake = FakeJudge0(polls_before_done=3)
    runs = await client(fake).run("echo", [("1", "1")], 1, 1024)
    assert runs[0].verdict == "ok"
    polls = [r for r in fake.requests if r.url.path == "/submissions/batch"]
    assert len([r for r in polls if r.method == "GET"]) == 4


@pytest.mark.parametrize(
    ("code", "verdict"),
    [
        ("tle", "time_limit"),
        ("crash", "runtime_error"),
        ("compile", "compilation_error"),
    ],
)
async def test_verdicts(fake, code, verdict):
    runs = await client(fake).run(code, [("", "")], 1, 1024)
    assert runs[0].verdict == verdict
    if code == "crash":
        assert "ZeroDivisionError" in runs[0].stderr


async def test_judge_internal_error_raises(fake):
    with pytest.raises(JudgeError, match="Judge failure"):
        await client(fake).run("internal", [("", "")], 1, 1024)


@pytest.mark.parametrize("status", [401, 422, 500, 503])
async def test_http_error_raises(fake, status):
    fake.post_status = status
    with pytest.raises(JudgeError):
        await client(fake).run("echo", [("1", "1")], 1, 1024)


async def test_connection_error_raises():
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    j = JudgeClient(base_url="http://judge0", transport=httpx.MockTransport(refuse))
    with pytest.raises(JudgeError, match="refused"):
        await j.run("echo", [("1", "1")], 1, 1024)


async def test_malformed_response_raises():
    j = JudgeClient(
        base_url="http://judge0",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text="<html>")),
    )
    with pytest.raises(JudgeError):
        await j.run("echo", [("1", "1")], 1, 1024)


async def test_poll_timeout_raises(fake):
    fake.pending_forever = True
    j = client(fake, timeout=0.05)
    with pytest.raises(JudgeError, match="Timed out"):
        await j.run("echo", [("1", "1")], 1, 1024)
