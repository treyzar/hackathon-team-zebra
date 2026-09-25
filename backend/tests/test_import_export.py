import json
from pathlib import Path

import pytest
from conftest import requires_db
from pydantic import TypeAdapter, ValidationError
from test_api import programming

from courses.export_import import (
    EXPORT_SCHEMA_VERSION,
    _collect_referenced_file_ids,
    _prune_missing_files,
    _unique_slug,
)
from courses.schemas import CourseDocument
from steps import StepPayload

SAMPLES = Path(__file__).resolve().parents[2] / "samples" / "courses"
payload_adapter = TypeAdapter(StepPayload)
document_adapter = TypeAdapter(CourseDocument)


def test_bundled_examples_match_the_current_schema():
    for name in ("import-example.json", "scratch-course.json"):
        raw = (SAMPLES / name).read_bytes()
        doc = document_adapter.validate_json(raw)
        assert doc.schema_version == EXPORT_SCHEMA_VERSION
        assert doc.course.modules


def test_schema_version_must_be_current():
    raw = json.dumps(
        {"schema_version": 1, "course": {"slug": "x", "title": "X", "modules": []}}
    )
    with pytest.raises(ValidationError):
        document_adapter.validate_json(raw)


def test_unknown_step_type_rejected():
    with pytest.raises(ValidationError):
        payload_adapter.validate_python(
            {
                "type": "short_answer",
                "max_score": 1,
                "content": {"question": {"type": "doc"}},
                "answer_key": {"checker": "number", "value": 0},
                "settings": {"grading": "auto"},
            }
        )


def test_is_published_in_course_rejected():
    raw = json.dumps(
        {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "course": {
                "slug": "x",
                "title": "X",
                "modules": [],
                "is_published": True,
            },
        }
    )
    with pytest.raises(ValidationError):
        document_adapter.validate_json(raw)


@pytest.mark.parametrize(
    "bad",
    [
        {
            "type": "theory",
            "max_score": 5,
            "content": {"body": {"type": "doc"}},
            "extra": 1,
        },
        {
            "type": "single_choice",
            "max_score": 1,
            "content": {"question": {"type": "doc"}, "options": []},
            "answer_key": {"correct": "x"},
        },
    ],
)
def test_payload_extra_and_minimal_checks(bad):
    with pytest.raises(ValidationError):
        payload_adapter.validate_python(bad)


def test_unique_slug_appends_suffix():
    assert _unique_slug("python", set()) == "python"
    assert _unique_slug("python", {"python"}) == "python-2"
    assert _unique_slug("python", {"python", "python-2"}) == "python-3"


def test_collect_referenced_file_ids_walks_rich_text_and_tests():
    payload = {
        "content": {
            "question": {
                "type": "doc",
                "content": [
                    {"type": "image", "attrs": {"file_id": 11}},
                ],
            }
        },
        "answer_key": {
            "files": [21, 22],
            "test_groups": [
                {
                    "tests": [
                        {"input_file": 31, "output_file": 32},
                        {"input": "text", "output": "text"},
                    ]
                }
            ],
        },
    }
    assert _collect_referenced_file_ids(payload) == {11, 21, 22, 31, 32}


def test_prune_drops_missing_files_but_keeps_the_rest():
    payload = {
        "content": {
            "question": {
                "type": "doc",
                "content": [
                    {"type": "image", "attrs": {"file_id": 11}},
                    {"type": "image", "attrs": {"file_id": 99}},
                ],
            }
        },
        "answer_key": {
            "files": [21, 99],
            "test_groups": [
                {
                    "tests": [
                        {"input_file": 31, "output_file": 99},
                        {"input": "text", "output": "text"},
                    ]
                }
            ],
        },
    }
    dropped = _prune_missing_files(payload, available={11, 21, 31})
    assert dropped == 3
    assert payload["answer_key"]["files"] == [21]
    assert payload["answer_key"]["test_groups"][0]["tests"] == [
        {"input": "text", "output": "text"}
    ]


def test_prune_on_empty_available_keeps_text_tests():
    payload = {
        "answer_key": {
            "test_groups": [
                {
                    "tests": [
                        {"input": "in", "output": "out"},
                        {"input_file": 1, "output_file": 2},
                    ]
                }
            ]
        }
    }
    assert _prune_missing_files(payload, available=set()) == 1


@requires_db
async def test_import_export_round_trip_all_types(client, admin):
    source = (SAMPLES / "import-example.json").read_bytes()

    first = await client.post(
        "/admin/courses/import",
        files={"file": ("course.json", source, "application/json")},
        headers=admin[1],
    )
    assert first.status_code == 201, first.text
    assert first.json()["warnings"] == []

    exported = await client.get(
        f"/admin/courses/{first.json()['course_id']}/export", headers=admin[1]
    )
    assert exported.status_code == 200
    document = exported.json()
    assert document["schema_version"] == 2

    again = await client.post(
        "/admin/courses/import",
        files={"file": ("again.json", exported.content, "application/json")},
        headers=admin[1],
    )
    assert again.status_code == 201, again.text
    assert again.json()["slug"] == "python-basics-2"
    assert all("занят" in w for w in again.json()["warnings"])

    second = await client.get(
        f"/admin/courses/{again.json()['course_id']}/export", headers=admin[1]
    )
    second_document = second.json()
    second_document["course"]["slug"] = document["course"]["slug"]
    assert second_document == document


@requires_db
async def test_import_slug_collision_reports_warning(client, admin):
    body = json.dumps(
        {
            "schema_version": 2,
            "course": {
                "slug": "python",
                "title": "P",
                "modules": [
                    {"title": "M", "steps": []},
                ],
            },
        }
    ).encode()
    r1 = await client.post(
        "/admin/courses/import",
        files={"file": ("a.json", body, "application/json")},
        headers=admin[1],
    )
    assert r1.json()["slug"] == "python"

    r2 = await client.post(
        "/admin/courses/import",
        files={"file": ("b.json", body, "application/json")},
        headers=admin[1],
    )
    assert r2.json()["slug"] == "python-2"
    assert any("занят" in w for w in r2.json()["warnings"])


@requires_db
async def test_import_always_creates_draft(client, admin):
    source = (SAMPLES / "import-example.json").read_bytes()
    r = await client.post(
        "/admin/courses/import",
        files={"file": ("c.json", source, "application/json")},
        headers=admin[1],
    )
    tree = await client.get(f"/admin/courses/{r.json()['course_id']}", headers=admin[1])
    assert tree.json()["is_published"] is False


@requires_db
async def test_import_reports_missing_file_references(client, admin, upload):
    real = await upload(admin[1], b"1\n", purpose="answer_key")
    payload = programming()
    payload["answer_key"]["test_groups"][0]["tests"] = [
        {"input": "3\n", "output": "9"},
        {"input_file": real, "output_file": 999999},
    ]
    body = json.dumps(
        {
            "schema_version": 2,
            "course": {
                "slug": "files",
                "title": "F",
                "modules": [
                    {"title": "M", "steps": [{"is_hidden": False, "payload": payload}]},
                ],
            },
        }
    ).encode()
    r = await client.post(
        "/admin/courses/import",
        files={"file": ("d.json", body, "application/json")},
        headers=admin[1],
    )
    assert r.status_code == 201, r.text
    assert any("не найдены" in w for w in r.json()["warnings"])


@requires_db
async def test_import_per_group_mismatch_rejected(client, admin):
    payload = programming(scoring="per_group")
    payload["max_score"] = 99
    body = json.dumps(
        {
            "schema_version": 2,
            "course": {
                "slug": "bad",
                "title": "B",
                "modules": [
                    {"title": "M", "steps": [{"is_hidden": False, "payload": payload}]},
                ],
            },
        }
    ).encode()
    r = await client.post(
        "/admin/courses/import",
        files={"file": ("e.json", body, "application/json")},
        headers=admin[1],
    )
    assert r.status_code == 422
    assert "must equal max_score" in r.text


@requires_db
async def test_import_and_export_require_admin(client, make_user):
    body = b'{"schema_version":2,"course":{"slug":"x","title":"X","modules":[]}}'
    for role in ("student", "curator"):
        _, h = await make_user(role)
        r = await client.post(
            "/admin/courses/import",
            files={"file": ("a.json", body, "application/json")},
            headers=h,
        )
        assert r.status_code == 403
