from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from courses import service
from courses.models import Course, Module, Step, StepRevision
from files.models import File, FileStatus
from models import User
from steps import StepPayload
from steps.base import Schema


EXPORT_SCHEMA_VERSION = 1

_payload_adapter = TypeAdapter(StepPayload)

def unprocessable(msg = "Unprocessable") -> HTTPException:
    return HTTPException(HTTPException.HTTP_422_UNPROCESSABLE_CONTENT, detail=msg)

async def export_course(db: AsyncSession, course: Course) -> dict[str, Any]:
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



#import

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


def _require_string(value: Any, what: str, max_len: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise unprocessable("{what} должен быть непустой строкой")
    if max_len is not None and len(value) > max_len:
        raise unprocessable(f"{what} длиннее {max_len} символов")
    return value.strip()


async def import_course(
    db: AsyncSession, user: User, raw: bytes
) -> tuple[Course, list[str]]:
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as e:
        raise unprocessable(f"Файл не является JSON: {e}") from e

    document = _require_mapping(document, "файл")
    if document.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise unprocessable(f"Неизвестная версия схемы: {document.get('schema_version')!r}")
    payload = _require_mapping(document.get("course"), "поле `course`")

    warnings: list[str] = []

    slug_base = _require_string(payload.get("slug"), "slug", max_len=100)
    taken = set(await db.scalars(select(Course.slug)))
    slug = _unique_slug(slug_base, taken)
    if slug != slug_base:
        warnings.append(
            f"Адрес «{slug_base}» занят, импортировано как «{slug}»"
        )

    title = _require_string(payload.get("title"), "title", max_len=200)
    description = payload.get("description")
    if not isinstance(description, dict) or description.get("type") != "doc":
        description = {"type": "doc", "content": []}

    step_access_raw = payload.get("step_access", "all")
    try:
        from courses.models import StepAccess

        step_access = StepAccess(step_access_raw)
    except ValueError as e:
        raise unprocessable(f"Неизвестный step_access: {step_access_raw!r}") from e

    course = Course(
        slug=slug,
        title=title,
        description=description,
        is_published=False,
        step_access=step_access,
    )
    db.add(course)
    await db.flush()

    # --- modules & steps ----------------------------------------------------
    modules_raw = payload.get("modules")
    if not isinstance(modules_raw, list):
        raise unprocessable("`modules` должен быть списком")

    for module_index, module_raw in enumerate(modules_raw):
        module_raw = _require_mapping(module_raw, f"модуль #{module_index + 1}")
        module_title = _require_string(
            module_raw.get("title"), f"название модуля #{module_index + 1}", max_len=200
        )
        module = Module(
            course_id=course.id, title=module_title, position=module_index
        )
        db.add(module)
        await db.flush()

        steps_raw = module_raw.get("steps") or []
        if not isinstance(steps_raw, list):
            raise unprocessable(f"`steps` модуля #{module_index + 1} должен быть списком")

        for step_index, step_raw in enumerate(steps_raw):
            where = f"шаг {module_index + 1}.{step_index + 1}"
            step_raw = _require_mapping(step_raw, where)

            try:
                parsed = _payload_adapter.validate_python(step_raw)
            except ValidationError as e:
                first = e.errors(include_url=False)[0] if e.errors() else {}
                loc = ".".join(str(x) for x in first.get("loc", ())) or "payload"
                raise unprocessable(f"{where}: {loc}: {first.get('msg', 'некорректный payload')}") from e

            dumped = json.loads(parsed.model_dump_json())
            wanted = _collect_referenced_file_ids(dumped)
            available = await _live_file_ids(db, wanted)
            dropped = _prune_missing_files(dumped, available)
            if dropped:
                warnings.append(
                    f"{where}: {dropped} ссылок на файлы не найдены и отброшены"
                )
            try:
                parsed = _payload_adapter.validate_python(dumped)
            except ValidationError as e:
                first = e.errors(include_url=False)[0] if e.errors() else {}
                raise unprocessable(
                    f"{where}: после очистки файловых ссылок payload некорректен: "
                    f"{first.get('msg', 'ошибка')}",
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