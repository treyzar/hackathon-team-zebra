from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from courses.models import Course, Module, Step, StepRevision
from files.models import File, FileStatus
from models import User
from steps.base import FileInfo
from steps.registry import ParsedRevision, StepPayloadBase, get_type, parse_revision
from submissions.models import Submission


def now() -> datetime:
    return datetime.now(UTC)


def not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


async def get_course(db: AsyncSession, course_id: int) -> Course:
    course = await db.get(Course, course_id)
    if not course or course.deleted_at:
        raise not_found("Course")
    return course


async def get_module(db: AsyncSession, module_id: int) -> Module:
    module = await db.scalar(
        select(Module)
        .join(Course, Course.id == Module.course_id)
        .where(
            Module.id == module_id,
            Module.deleted_at.is_(None),
            Course.deleted_at.is_(None),
        )
    )
    if not module:
        raise not_found("Module")
    return module


async def get_step(
    db: AsyncSession, step_id: int, *, for_student: bool = False
) -> tuple[Step, StepRevision, Module]:
    """Live step with its current revision. Students only get steps that are
    visible: not hidden, in a published course."""
    query = (
        select(Step, StepRevision, Module)
        .join(StepRevision, StepRevision.id == Step.current_revision_id)
        .join(Module, Module.id == Step.module_id)
        .join(Course, Course.id == Module.course_id)
        .where(
            Step.id == step_id,
            Step.deleted_at.is_(None),
            Module.deleted_at.is_(None),
            Course.deleted_at.is_(None),
        )
    )
    if for_student:
        query = query.where(Course.is_published, Step.is_hidden.is_(False))
    row = (await db.execute(query)).one_or_none()
    if not row:
        raise not_found("Step")
    return tuple(row)


async def live_modules(db: AsyncSession, course_id: int) -> list[Module]:
    """The course's modules (not deleted) in course order."""
    query = (
        select(Module)
        .where(Module.course_id == course_id, Module.deleted_at.is_(None))
        .order_by(Module.position, Module.id)
    )
    return list(await db.scalars(query))


@dataclass
class OrderedStep:
    id: int
    module_id: int
    type: str
    # From the current revision.
    max_score: int
    settings: dict


async def visible_steps_in_order(db: AsyncSession, course_id: int) -> list[OrderedStep]:
    """The course's visible steps in the order students go through them:
    modules by position, then steps by position. Hidden and deleted steps are
    left out. The one place that defines course order (access, deadlines,
    progress)."""
    rows = await db.execute(
        select(
            Step.id,
            Step.module_id,
            Step.type,
            StepRevision.max_score,
            StepRevision.settings,
        )
        .join(Module, Module.id == Step.module_id)
        .join(StepRevision, StepRevision.id == Step.current_revision_id)
        .where(
            Module.course_id == course_id,
            Module.deleted_at.is_(None),
            Step.deleted_at.is_(None),
            Step.is_hidden.is_(False),
        )
        .order_by(Module.position, Module.id, Step.position, Step.id)
    )
    return [OrderedStep(*row) for row in rows]


def parse(step: Step, rev: StepRevision) -> ParsedRevision:
    return parse_revision(
        step.type,
        rev.content,
        rev.answer_key,
        rev.settings,
        rev.schema_version,
        rev.max_score,
    )


async def next_position(db: AsyncSession, column, parent_column, parent_id) -> int:
    current = await db.scalar(
        select(func.max(column)).where(parent_column == parent_id)
    )
    return 0 if current is None else current + 1


async def reorder(db: AsyncSession, items: list, ids: list[int]) -> None:
    by_id = {item.id: item for item in items}
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "ids must list every item exactly once",
        )
    for position, item_id in enumerate(ids):
        by_id[item_id].position = position


async def check_authored_files(db: AsyncSession, payload: StepPayloadBase) -> None:
    """Files the step refers to must be uploaded and suit the step type."""
    t = get_type(payload.type)
    ids = set(t.authored_files(payload.content, payload.answer_key))
    if not ids:
        return
    found = (
        await db.scalars(
            select(File).where(File.id.in_(ids), File.status == FileStatus.READY)
        )
    ).all()
    missing = ids - {f.id for f in found}
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Unknown or not uploaded files: {sorted(missing)}",
        )
    infos = {f.id: FileInfo(f.id, f.mime, f.size, f.purpose.value) for f in found}
    try:
        t.check_authored_files(payload.content, payload.answer_key, infos)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e


async def add_revision(
    db: AsyncSession,
    step: Step,
    payload: StepPayloadBase,
    author: User,
    comment: str | None,
    is_breaking: bool,
) -> StepRevision:
    await check_authored_files(db, payload)
    number = (
        await db.scalar(
            select(func.max(StepRevision.number)).where(StepRevision.step_id == step.id)
        )
        or 0
    ) + 1
    rev = StepRevision(
        step_id=step.id,
        number=number,
        content=payload.content.model_dump(mode="json"),
        answer_key=payload.answer_key.model_dump(mode="json"),
        settings=payload.settings.model_dump(mode="json"),
        schema_version=get_type(step.type).schema_version,
        max_score=payload.max_score,
        author_id=author.id,
        comment=comment,
        is_breaking=is_breaking,
    )
    db.add(rev)
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Step was changed concurrently, reload it"
        ) from e
    step.current_revision_id = rev.id
    if is_breaking:
        await db.execute(
            update(Submission)
            .where(Submission.step_id == step.id, Submission.is_outdated.is_(False))
            .values(is_outdated=True)
        )
    return rev


def soft_delete(item) -> None:
    item.deleted_at = now()
