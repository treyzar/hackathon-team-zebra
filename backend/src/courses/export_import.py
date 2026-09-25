from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError, TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from courses import service
from courses.models import Course, Module, Step, StepRevision
from courses.schemas import (
    CourseCreate,
    ModuleIn,
    ExportedCourse,
    ExportedModule,
    ExportedStep,
    CourseDocument,
    EXPORT_SCHEMA_VERSION
)
from files.models import File, FileStatus
from models import User
from steps import StepPayload

_payload_adapter = TypeAdapter(StepPayload)

def unprocessable(msg: str = "Unprocessable") -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=msg)

def _first_error(error: ValidationError, where: str = "") -> str:
    errors = error.errors(include_url=False)
    first = errors[0] if errors else {}
    loc = ".".join(str(x) for x in first.get("loc", ())) or "payload"
    msg = first.get("msg", "некорректное значение")
    prefix = f"{where}: " if where else ""
    return f"{prefix}{loc}: {msg}"


def _unique_slug(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def _collect_referenced_file_ids(payload: dict[str, Any]) -> set[int]:
    ids: set[int] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("file_id", "input_file", "output_file") and isinstance(item, int):
                    ids.add(item)
                elif key == "files" and isinstance(item, list):
                    ids.update(x for x in item if isinstance(x, int))
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return ids


def _prune_missing_files(payload: dict[str, Any], available: set[int]) -> int:
    dropped = 0

    def prune_test(tests: list[Any]) -> list[Any]:
        nonlocal dropped
        kept: list[Any] = []
        for test in tests:
            if not isinstance(test, dict):
                kept.append(test)
                continue
            broken = any(
                isinstance(test.get(key), int) and test[key] not in available
                for key in ("input_file", "output_file")
            )
            if broken:
                dropped += 1
                continue
            kept.append(test)
        return kept

    def walk(value: Any) -> None:
        nonlocal dropped
        if isinstance(value, dict):
            if isinstance(value.get("tests"), list):
                value["tests"] = prune_test(value["tests"])
            if isinstance(value.get("files"), list) and all(
                isinstance(x, int) or x is None for x in value["files"]
            ):
                kept = [x for x in value["files"] if isinstance(x, int) and x in available]
                dropped += len(value["files"]) - len(kept)
                value["files"] = kept
            for key in ("file_id", "input_file", "output_file"):
                if isinstance(value.get(key), int) and value[key] not in available:
                    value.pop(key)
                    dropped += 1
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return dropped


async def _live_file_ids(db: AsyncSession, ids: set[int]) -> set[int]:
    if not ids:
        return set()
    rows = await db.scalars(
        select(File.id).where(File.id.in_(ids), File.status == FileStatus.READY)
    )
    return set(rows)


def _require_mapping(value: Any, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise unprocessable(f"{what} должен быть объектом")
    return value


async def import_course(
    db: AsyncSession, user: User, raw: bytes
) -> tuple[Course, list[str]]:
    try:
        document = CourseDocument.model_validate_json(raw)
    except ValidationError as e:
        raise unprocessable(_first_error(e, "файл")) from e

    data = document.course
    warnings: list[str] = []

    taken = set(await db.scalars(select(Course.slug)))
    slug = _unique_slug(data.slug, taken)
    if slug != data.slug:
        warnings.append(f"Адрес «{data.slug}» занят, импортировано как «{slug}»")

    course = Course(
        slug=slug,
        title=data.title,
        description=data.description.model_dump(mode="json"),
        is_published=False,
        step_access=data.step_access,
    )
    db.add(course)
    await db.flush()

    for module_index, module in enumerate(data.modules):
        db_module = Module(
            course_id=course.id, title=module.title, position=module_index
        )
        db.add(db_module)
        await db.flush()

        for step_index, exported in enumerate(module.steps):
            where = f"шаг {module_index + 1}.{step_index + 1}"
            payload = exported.payload.model_dump(mode="json")
            wanted = _collect_referenced_file_ids(payload)
            available = await _live_file_ids(db, wanted)
            dropped = _prune_missing_files(payload, available)
            if dropped:
                warnings.append(
                    f"{where}: {dropped} ссылок на файлы не найдены и отброшены"
                )
            try:
                parsed = _payload_adapter.validate_python(payload)
            except ValidationError as e:
                raise unprocessable(
                    f"{where}: после очистки файловых ссылок payload "
                    f"некорректен: {_first_error(e)}"
                ) from e

            step = Step(
                module_id=db_module.id,
                type=parsed.type,
                position=step_index,
                is_hidden=exported.is_hidden,
            )
            db.add(step)
            await db.flush()

            await service.add_revision(
                db, step, parsed, user, "Импорт курса", is_breaking=False
            )

    return course, warnings


async def export_as_json(db: AsyncSession, course: Course) -> dict[str, Any]:
    modules = await service.live_modules(db, course.id)
    steps = list(
        await db.scalars(
            select(Step)
            .where(
                Step.module_id.in_([m.id for m in modules]),
                Step.deleted_at.is_(None),
            )
            .order_by(Step.position, Step.id)
        )
    )
    revision_ids = [s.current_revision_id for s in steps if s.current_revision_id]
    revisions: dict[int, StepRevision] = {
        r.id: r
        for r in await db.scalars(
            select(StepRevision).where(StepRevision.id.in_(revision_ids))
        )
    }

    by_module: dict[int, list[ExportedStep]] = {m.id: [] for m in modules}
    for step in steps:
        rev = revisions.get(step.current_revision_id or -1)
        if rev is None:
            continue
        parsed = service.parse(step, rev)
        payload = _payload_adapter.validate_python(            {
                "type": parsed.type.key,
                "max_score": parsed.max_score,
                "content": parsed.content,
                "answer_key": parsed.answer_key,
                "settings": parsed.settings,
            })
        by_module[step.module_id].append(ExportedStep(is_hidden=step.is_hidden, payload=payload))

    document = CourseDocument(
        schema_version=EXPORT_SCHEMA_VERSION,
        course=ExportedCourse(
            slug=course.slug,
            title=course.title,
            description=course.description,
            step_access=course.step_access,
            modules=[
                ExportedModule(title=m.title, steps=by_module[m.id]) for m in modules
            ],
        ),
    )
    return document.model_dump(mode="json")