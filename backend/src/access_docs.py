"""States who may call each endpoint in its OpenAPI description (/docs).

The role line is derived from the endpoint's dependencies, so it cannot drift
from the actual checks: ``require_roles`` gives the roles, the OAuth2 token
dependency means any signed-in user, nothing means public. Rules checked in
the endpoint body (e.g. "only your own submissions") are added with
``@access_note``.
"""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.security import OAuth2PasswordBearer

from models import Role

ACCESS_PREFIX = "**Доступ:**"
ROLE_NAMES = {
    Role.STUDENT: "ученик",
    Role.CURATOR: "куратор",
    Role.ADMIN: "администратор",
}


def access_note(text: str) -> Callable:
    """Extra access rules of an endpoint, shown after the role line."""

    def mark(endpoint: Callable) -> Callable:
        endpoint.__access_note__ = text
        return endpoint

    return mark


def _calls(dependant) -> list:
    calls = []
    for dep in dependant.dependencies:
        calls.append(dep.call)
        calls += _calls(dep)
    return calls


def access_text(route: APIRoute) -> str:
    calls = _calls(route.dependant)
    role_sets = [call.roles for call in calls if hasattr(call, "roles")]
    if role_sets:
        # Several role checks: all of them must pass.
        allowed = frozenset.intersection(*role_sets)
        who = ", ".join(ROLE_NAMES[r] for r in Role if r in allowed)
    elif any(isinstance(call, OAuth2PasswordBearer) for call in calls):
        who = "любой вошедший пользователь"
    else:
        who = "без авторизации"
    text = f"{ACCESS_PREFIX} {who}."
    note = getattr(route.endpoint, "__access_note__", None)
    return f"{text}\n\n{note}" if note else text


def _routes(router):
    for route in router.routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):  # an included router
            yield from _routes(route.original_router)


def document_access(app: FastAPI) -> None:
    """Prepend the access line to every endpoint description. Call once,
    after all routers are included and before the first request."""
    for route in _routes(app.router):
        if route.description.startswith(ACCESS_PREFIX):
            continue
        text = access_text(route)
        route.description = (
            f"{text}\n\n{route.description}" if route.description else text
        )
