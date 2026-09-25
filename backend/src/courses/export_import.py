from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from courses import service
from courses.models import Course, Module, Step, StepRevision
from courses.schemas import CourseCreate, ModuleIn
from files.models import File, FileStatus
from models import User
from steps import StepPayload


EXPORT_SCHEMA_VERSION = 1

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

    by_module: dict[int, list[dict[str, Any]]] = {m.id: [] for m in modules}
    for step in steps:
        rev = revisions.get(step.current_revision_id or -1)
        if rev is None:
            continue
        by_module[step.module_id].append(
            {
                "type": step.type,
                "is_hidden": step.is_hidden,
                "max_score": rev.max_score,
                "content": rev.content,
                "answer_key": rev.answer_key,
                "settings": rev.settings,
            }
        )

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "course": {
            "slug": course.slug,
            "title": course.title,
            "description": course.description,
            "step_access": course.step_access.value,
            "is_published": course.is_published,
            "modules": [
                {"title": m.title, "steps": by_module[m.id]} for m in modules
            ],
        },
    }


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
        document = json.loads(raw)
    except json.JSONDecodeError as e:
        raise unprocessable(f"Файл не является JSON: {e}") from e

    document = _require_mapping(document, "файл")
    if document.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise unprocessable(
            f"Неизвестная версия схемы: {document.get('schema_version')!r}"
        )
    payload = _require_mapping(document.get("course"), "поле `course`")

    warnings: list[str] = []

    try:
        data = CourseCreate.model_validate(payload)
    except ValidationError as e:
        raise unprocessable(_first_error(e, "поле `course`")) from e

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

    modules_raw = payload.get("modules")
    if not isinstance(modules_raw, list):
        raise unprocessable("`modules` должен быть списком")

    for module_index, module_raw in enumerate(modules_raw):
        where = f"модуль #{module_index + 1}"
        module_raw = _require_mapping(module_raw, where)

        try:
            module_data = ModuleIn.model_validate(module_raw)
        except ValidationError as e:
            raise unprocessable(_first_error(e, where)) from e

        module = Module(
            course_id=course.id,
            title=module_data.title,
            position=module_index,
        )
        db.add(module)
        await db.flush()

        steps_raw = module_raw.get("steps") or []
        if not isinstance(steps_raw, list):
            raise unprocessable(
                f"`steps` модуля #{module_index + 1} должен быть списком"
            )

        for step_index, step_raw in enumerate(steps_raw):
            step_where = f"шаг {module_index + 1}.{step_index + 1}"
            step_raw = _require_mapping(step_raw, step_where)

            try:
                parsed = _payload_adapter.validate_python(step_raw)
            except ValidationError as e:
                raise unprocessable(_first_error(e, step_where)) from e

            dumped = json.loads(parsed.model_dump_json())
            wanted = _collect_referenced_file_ids(dumped)
            available = await _live_file_ids(db, wanted)
            dropped = _prune_missing_files(dumped, available)
            if dropped:
                warnings.append(
                    f"{step_where}: {dropped} ссылок на файлы не найдены и отброшены"
                )
            try:
                parsed = _payload_adapter.validate_python(dumped)
            except ValidationError as e:
                raise unprocessable(
                    f"{step_where}: после очистки файловых ссылок payload "
                    f"некорректен: {_first_error(e)}"
                ) from e

            step = Step(
                module_id=module.id,
                type=parsed.type,
                position=step_index,
                is_hidden=bool(step_raw.get("is_hidden", False)),
            )
            db.add(step)
            await db.flush()

            await service.add_revision(
                db, step, parsed, user, "Импорт курса", is_breaking=False
            )

    return course, warnings