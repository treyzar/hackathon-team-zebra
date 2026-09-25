"""Every endpoint states in /docs who may call it (no database needed)."""

import pytest

from access_docs import ACCESS_PREFIX, document_access


@pytest.fixture(scope="module")
def operations():
    from server import app

    ops = {}
    for path, methods in app.openapi()["paths"].items():
        for method, op in methods.items():
            ops[f"{method.upper()} {path}"] = op.get("description", "")
    return ops


def access(operations, key):
    return operations[key].split("\n")[0]


def test_every_endpoint_has_access_line(operations):
    missing = [k for k, d in operations.items() if not d.startswith(ACCESS_PREFIX)]
    assert not missing


@pytest.mark.parametrize(
    ("endpoint", "who"),
    [
        ("POST /api/auth/login", "без авторизации"),
        ("GET /health", "без авторизации"),
        ("GET /api/user/me", "любой вошедший пользователь"),
        ("GET /api/courses", "любой вошедший пользователь"),
        ("POST /api/steps/{step_id}/submissions", "любой вошедший пользователь"),
        ("GET /api/review/submissions", "куратор, администратор"),
        ("POST /api/admin/courses", "администратор"),
        ("PUT /api/admin/groups/{group_id}/students/{user_id}", "администратор"),
        ("PATCH /api/admin/users/{user_id}/role", "администратор"),
    ],
)
def test_roles_derived_from_dependencies(operations, endpoint, who):
    assert access(operations, endpoint) == f"{ACCESS_PREFIX} {who}."


def test_extra_rules_and_docstrings_kept(operations):
    review = operations["GET /api/review/submissions/{submission_id}"]
    assert "только решения учеников своих групп" in review
    step = operations["GET /api/steps/{step_id}"]
    assert "последовательным доступом" in step
    # The endpoint docstring stays after the access part.
    assert operations["POST /api/admin/steps/{step_id}/revisions"].endswith(
        "Save a new revision of the step; history is kept."
    )


def test_document_access_is_idempotent():
    from server import app

    document_access(app)
    document_access(app)
    desc = app.openapi()["paths"]["/api/courses"]["get"]["description"]
    assert desc.count(ACCESS_PREFIX) == 1
