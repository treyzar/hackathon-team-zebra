from __future__ import annotations

import io
import json
import zipfile
from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from fontTools.ttLib.tables.grUtils import entries
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from courses import service
from courses.models import Course, Module, Step, StepRevision
from courses.schemas import (
    EXPORT_SCHEMA_VERSION,
    CourseDocument,
    ExportedCourse,
    ExportedModule,
    ExportedStep,
)
from files import storage
from files.models import File, FilePurpose, FileStatus
from files.schemas import (
    ARCHIVED_FILES_PREFIX,
    COURSE_DOCUMENT_FILENAME,
    MANIFEST_FILENAME,
    ArchiveManifest,
    ManifestFile,
)
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


_DROPPED_FILE_ID = 0
_FILE_REFERENCE_KEYS = ("file_id", "input_file", "output_file")


def _replace_file_ids(value: Any, mapping: dict[int, int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _FILE_REFERENCE_KEYS and isinstance(item, int):
                value[key] = mapping.get(item, _DROPPED_FILE_ID)
            elif key == "files" and isinstance(item, list):
                value[key] = [
                    mapping.get(x, _DROPPED_FILE_ID) if isinstance(x, int) else x
                    for x in item
                ]
            else:
                _replace_file_ids(item, mapping)
    elif isinstance(value, list):
        for item in value:
            _replace_file_ids(item, mapping)


def _collect_referenced_file_ids(payload: dict[str, Any]) -> set[int]:
    ids: set[int] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("file_id", "input_file", "output_file") and isinstance(
                    item, int
                ):
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
                kept = [
                    x for x in value["files"] if isinstance(x, int) and x in available
                ]
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


_ARCHIVE_PURPOSES = frozenset({FilePurpose.CONTENT, FilePurpose.ANSWER_KEY})


async def _store_archive_files(
    db: AsyncSession,
    user: User,
    archive: zipfile.ZipFile,
    manifest: ArchiveManifest,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for entry in manifest.files:
        if entry.purpose not in _ARCHIVE_PURPOSES:
            raise unprocessable(
                f"Файл «{entry.filename}»: назначение «{entry.purpose.value}» "
                f"нельзя перенести в курс"
            )

        data = archive.read(entry.path)
        if len(data) != entry.size:
            raise unprocessable(
                f"Файл «{entry.filename}»: в манифесте {entry.size} байт, "
                f"в архиве {len(data)}"
            )

        file = File(
            owner_id=user.id,
            purpose=entry.purpose,
            status=FileStatus.READY,
            storage_key=f"{entry.purpose.value}/{uuid4().hex}",
            filename=entry.filename,
            mime=entry.mime,
            size=len(data),
        )
        db.add(file)
        await db.flush()
        await storage.write_object(file.storage_key, data, file.mime)
        mapping[entry.id] = file.id
    return mapping


async def import_course_archive(db, user, raw):
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipfile as e:
        raise unprocessable(
            "Поврежденнный или неподдерживаемый тип архива (не .zip)."
        ) from e

    with archive:
        names = set(archive.namelist())

        for required in (COURSE_DOCUMENT_FILENAME, MANIFEST_FILENAME):
            if required not in names:
                raise unprocessable(f"В архиве нет «{required}»")

        try:
            manifest = ArchiveManifest.model_validate_json(
                archive.read(MANIFEST_FILENAME)
            )
        except ValidationError as e:
            raise unprocessable(_first_error(e, MANIFEST_FILENAME)) from e

        if missing := manifest.paths() - names:
            listed = ", ".join(f"«{p}»" for p in sorted(missing))
            raise unprocessable(f"В архиве не обнаружены файлы: {listed}")

        try:
            raw_document = json.loads(archive.read(COURSE_DOCUMENT_FILENAME))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise unprocessable(f"«{COURSE_DOCUMENT_FILENAME}»: {e}") from e

        try:
            CourseDocument.model_validate(raw_document)
        except ValidationError as e:
            raise unprocessable(_first_error(e, "файл")) from e

        mapping = await _store_archive_files(db, user, archive, manifest)
        _replace_file_ids(raw_document, mapping)
        document = CourseDocument.model_validate(raw_document)
    return await import_course_document(db, user, document)


async def import_course_document(
    db: AsyncSession, user: User, document: CourseDocument
) -> tuple[Course, list[str]]:
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


async def import_course(
    db: AsyncSession, user: User, raw: bytes
) -> tuple[Course, list[str]]:
    if zipfile.is_zipfile(io.BytesIO(raw)):
        return await import_course_archive(db, user, raw)
    try:
        document = CourseDocument.model_validate_json(raw)
    except ValidationError as e:
        raise unprocessable(_first_error(e, "файл")) from e

    return await import_course_document(db, user, document)


async def export_as_archive(
    db: AsyncSession, course: Course, document: dict[str, Any]
) -> bytes | None:
    file_ids = _collect_referenced_file_ids(document)

    if not file_ids:
        return None

    rows = await db.scalars(
        select(File).where(File.id.in_(file_ids), File.status == FileStatus.READY)
    )
    files = {file.id: file for file in rows}

    if not files:
        return None

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_id, file in files.items():
            data = await storage.read_object(file.storage_key)
            exported_name = PurePosixPath(file.filename).name or f"file_{file_id}"
            exported_path = f"{ARCHIVED_FILES_PREFIX}{file_id}__{exported_name}"

            archive.writestr(exported_path, data)
            entries.append(
                ManifestFile(
                    id=file_id,
                    path=exported_path,
                    purpose=file.purpose,
                    mime=file.mime,
                    size=len(data),
                )
            )
        archive.writestr(
            COURSE_DOCUMENT_FILENAME, json.dumps(document, ensure_ascii=False, indent=2)
        )
        archive.writestr(
            MANIFEST_FILENAME, ArchiveManifest(files=entries).model_dump_json(indent=2)
        )
    return buffer.getvalue()


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
        payload = _payload_adapter.validate_python(
            {
                "type": parsed.type.key,
                "max_score": parsed.max_score,
                "content": parsed.content,
                "answer_key": parsed.answer_key,
                "settings": parsed.settings,
            }
        )
        by_module[step.module_id].append(
            ExportedStep(is_hidden=step.is_hidden, payload=payload)
        )

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
