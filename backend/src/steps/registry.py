from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, create_model, model_validator

from steps.base import CommonSettings, Schema, StepType

_types: dict[str, StepType] = {}


def register[T: type[StepType]](cls: T) -> T:
    if cls.key in _types:
        raise RuntimeError(f"Step type {cls.key!r} registered twice")
    _types[cls.key] = cls()
    return cls


def get_type(key: str) -> StepType:
    return _types[key]


def all_types() -> dict[str, StepType]:
    return dict(_types)


class StepPayloadBase(Schema):
    """Authored step data: common part of every type's generated payload."""

    type: str
    max_score: int = Field(default=1, ge=0, le=1000)
    content: Schema
    answer_key: Schema
    settings: CommonSettings

    @model_validator(mode="after")
    def _cross_validate(self):
        t = get_type(self.type)
        if t.fixed_max_score is not None:
            self.max_score = t.fixed_max_score
        t.validate(self.content, self.answer_key, self.settings, self.max_score)
        _check_checklist(self.settings, self.max_score)
        return self


def _check_checklist(settings: CommonSettings, max_score: int) -> None:
    """Checked criteria are the whole score: so they add up to the maximum,
    and only a curator's review uses them."""
    if not settings.checklist:
        return
    if not settings.grading.uses_review:
        raise ValueError("A checklist needs grading by a curator")
    total = round(sum(item.points for item in settings.checklist), 2)
    if total != max_score:
        raise ValueError(
            f"Checklist points ({total:g}) must add up to max_score ({max_score})"
        )


def _payload_model(t: StepType) -> type[StepPayloadBase]:
    name = "".join(p.capitalize() for p in t.key.split("_")) + "Payload"
    return create_model(
        name,
        __base__=StepPayloadBase,
        type=(Literal[t.key], ...),
        content=(t.content_model, ...),
        answer_key=(
            t.answer_key_model,
            t.answer_key_model() if not t.answer_key_model.model_fields else ...,
        ),
        settings=(t.settings_model, t.settings_model()),
    )


def build_payload_union() -> Any:
    """Discriminated union of all registered types, for request validation
    and OpenAPI. Call after all types are imported."""
    models = tuple(_payload_model(t) for t in _types.values())
    return Annotated[
        models[0] if len(models) == 1 else _union(models), Field(discriminator="type")
    ]


def _union(models: tuple[type[BaseModel], ...]) -> Any:
    from typing import Union

    return Union[models]  # noqa: UP007 - built dynamically


@dataclass
class ParsedRevision:
    """A stored revision decoded into the type's models."""

    type: StepType
    content: Any
    answer_key: Any
    settings: Any
    max_score: int


def parse_revision(
    type_key: str,
    content: dict[str, Any],
    answer_key: dict[str, Any],
    settings: dict[str, Any],
    schema_version: int,
    max_score: int,
) -> ParsedRevision:
    t = get_type(type_key)
    data = {"content": content, "answer_key": answer_key, "settings": settings}
    if schema_version < t.schema_version:
        data = t.upgrade(data, schema_version)
    return ParsedRevision(
        type=t,
        content=t.content_model.model_validate(data["content"]),
        answer_key=t.answer_key_model.model_validate(data["answer_key"]),
        settings=t.settings_model.model_validate(data["settings"]),
        max_score=max_score,
    )
