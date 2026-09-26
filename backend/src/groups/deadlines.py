"""Course deadlines and deadlines of steps, per group.

A curator (for their own groups) or an admin sets a deadline on a step. A step
without its own deadline gets the deadline of the nearest following step that
has one, or the course deadline after the last step deadline. Only deadlines
people set are stored; inherited ones are computed when shown.
"""

from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AwareDatetime, BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import require_curator
from courses import service as courses_svc
from courses.models import Course, Enrollment, Module, Step, StepRevision
from courses.schemas import DeadlineView
from database import access_db
from groups.models import Deadline, Group, GroupCourseDeadline, GroupStudent
from groups.service import manageable_group
from models import Role, User
from notifications.models import NotificationType
from notifications.payloads import DeadlineChangedPayload
from notifications.service import create_notification

deadlines = APIRouter(prefix="/groups", tags=["deadlines"])


@dataclass
class Effective:
    due_at: datetime
    # None means the course deadline; otherwise the source step.
    source_step_id: int | None


async def effective_deadlines(
    db: AsyncSession, group_id: int | None, course_id: int
) -> dict[int, Effective]:
    """Deadline of each visible step: nearest following step deadline for the
    group, then the course deadline as a fallback."""
    course_deadline = await db.scalar(
        select(Course.deadline_at).where(Course.id == course_id)
    )
    if group_id is not None:
        group_deadline = await db.scalar(
            select(GroupCourseDeadline.due_at).where(
                GroupCourseDeadline.group_id == group_id,
                GroupCourseDeadline.course_id == course_id,
            )
        )
        if group_deadline is not None:
            course_deadline = group_deadline
    order = [s.id for s in await courses_svc.visible_steps_in_order(db, course_id)]
    own = (
        dict(
            (
                await db.execute(
                    select(Deadline.step_id, Deadline.due_at).where(
                        Deadline.group_id == group_id, Deadline.step_id.in_(order)
                    )
                )
            ).all()
        )
        if group_id is not None
        else {}
    )
    result: dict[int, Effective] = {}
    carry: Effective | None = (
        Effective(course_deadline, None) if course_deadline is not None else None
    )
    for step_id in reversed(order):
        if step_id in own:
            carry = Effective(own[step_id], step_id)
        if carry is not None:
            result[step_id] = carry
    return result


async def _notify_changed_deadline(
    db: AsyncSession,
    group_id: int,
    course_id: int,
    step_id: int | None,
    before: dict[int, Effective],
    previous_due: datetime | None = None,
) -> None:
    """Notify enrolled group students only when the effective schedule changed."""
    after = await effective_deadlines(db, group_id, course_id)
    if all(
        (before.get(key).due_at if key in before else None)
        == (after.get(key).due_at if key in after else None)
        for key in before.keys() | after.keys()
    ):
        return

    course = await db.get(Course, course_id)
    source = after.get(step_id) if step_id is not None else None
    previous = before.get(step_id) if step_id is not None else None
    if step_id is None:
        group_due = await db.scalar(
            select(GroupCourseDeadline.due_at).where(
                GroupCourseDeadline.group_id == group_id,
                GroupCourseDeadline.course_id == course_id,
            )
        )
        current_due = group_due if group_due is not None else course.deadline_at
    else:
        current_due = source.due_at if source else None
    step_title = None
    if step_id is not None:
        step = await db.get(Step, step_id)
        revision = (
            await db.get(StepRevision, step.current_revision_id) if step else None
        )
        step_title = courses_svc.get_step_title(revision.content) if revision else None
    payload = DeadlineChangedPayload(
        step_id=step_id,
        course_id=course_id,
        deadline=current_due,
        previous=previous.due_at if previous else previous_due,
        step_title=step_title,
        course_title=course.title,
    )
    students = await db.scalars(
        select(GroupStudent.user_id)
        .join(
            Enrollment,
            (Enrollment.user_id == GroupStudent.user_id)
            & (Enrollment.course_id == course_id),
        )
        .where(GroupStudent.group_id == group_id)
    )
    for user_id in students:
        await create_notification(
            db, user_id, NotificationType.DEADLINE_CHANGED, payload
        )


async def submission_deadlines(
    db: AsyncSession, subs: list
) -> dict[int, datetime | None]:
    """The deadline each submission is measured against: the effective one
    of the step for the author's current group. Computed, not stored, so
    extending a deadline also clears the "late" mark."""
    if not subs:
        return {}
    groups = dict(
        (
            await db.execute(
                select(GroupStudent.user_id, GroupStudent.group_id).where(
                    GroupStudent.user_id.in_({s.user_id for s in subs})
                )
            )
        ).all()
    )
    courses = dict(
        (
            await db.execute(
                select(Step.id, Module.course_id)
                .join(Module, Module.id == Step.module_id)
                .where(Step.id.in_({s.step_id for s in subs}))
            )
        ).all()
    )
    per_course: dict[tuple[int | None, int], dict[int, Effective]] = {}
    result: dict[int, datetime | None] = {}
    for s in subs:
        key = (groups.get(s.user_id), courses.get(s.step_id))
        if key[1] is None:
            result[s.id] = None
            continue
        if key not in per_course:
            per_course[key] = await effective_deadlines(db, *key)
        eff = per_course[key].get(s.step_id)
        result[s.id] = eff.due_at if eff else None
    return result


def is_late(sub, due_at: datetime | None) -> bool:
    return due_at is not None and sub.created_at > due_at


# --- API ---------------------------------------------------------------------


class GroupBrief(BaseModel):
    id: int
    name: str
    curator_id: int | None


class DeadlineIn(BaseModel):
    # With a timezone, e.g. 2026-10-01T23:59:00+03:00.
    due_at: AwareDatetime


class OwnDeadline(BaseModel):
    model_config = {"from_attributes": True}
    due_at: datetime
    set_by: int | None
    updated_at: datetime


class StepDeadline(BaseModel):
    step_id: int
    module_id: int
    module_title: str
    module_position: int
    step_position: int
    title: str
    type: str
    # What a person set on this step, if anything.
    own: OwnDeadline | None
    # What students see: own or inherited.
    effective: DeadlineView | None


class CourseDeadlineState(BaseModel):
    own: OwnDeadline | None
    effective_due_at: datetime | None


def view(step_id: int, eff: Effective | None) -> DeadlineView | None:
    if eff is None:
        return None
    return DeadlineView(
        due_at=eff.due_at,
        inherited=eff.source_step_id != step_id,
        source_step_id=eff.source_step_id,
    )


async def _live_step(db: AsyncSession, step_id: int) -> Step:
    step, _, _ = await courses_svc.get_step(db, step_id)
    return step


@deadlines.get("", response_model=list[GroupBrief])
@access_note("Куратор видит свои группы, администратор — все.")
async def list_groups(
    user: User = Depends(require_curator), db: AsyncSession = Depends(access_db)
):
    query = select(Group).order_by(Group.name)
    if user.role != Role.ADMIN:
        query = query.where(Group.curator_id == user.id)
    return [
        GroupBrief(id=g.id, name=g.name, curator_id=g.curator_id)
        for g in await db.scalars(query)
    ]


async def _course_deadline_state(
    db: AsyncSession, group_id: int, course: Course
) -> CourseDeadlineState:
    own = await db.scalar(
        select(GroupCourseDeadline).where(
            GroupCourseDeadline.group_id == group_id,
            GroupCourseDeadline.course_id == course.id,
        )
    )
    return CourseDeadlineState(
        own=OwnDeadline.model_validate(own) if own else None,
        effective_due_at=own.due_at if own else course.deadline_at,
    )


@deadlines.get(
    "/{group_id}/courses/{course_id}/deadline", response_model=CourseDeadlineState
)
@access_note("Куратор — только для своей группы, администратор — для любой.")
async def get_course_deadline(
    group_id: int,
    course_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    course = await courses_svc.get_course(db, course_id)
    return await _course_deadline_state(db, group_id, course)


@deadlines.put(
    "/{group_id}/courses/{course_id}/deadline", response_model=CourseDeadlineState
)
@access_note("Куратор — только для своей группы, администратор — для любой.")
async def set_course_deadline(
    group_id: int,
    course_id: int,
    data: DeadlineIn,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    course = await courses_svc.get_course(db, course_id)
    before = await effective_deadlines(db, group_id, course_id)
    deadline = await db.scalar(
        select(GroupCourseDeadline).where(
            GroupCourseDeadline.group_id == group_id,
            GroupCourseDeadline.course_id == course_id,
        )
    )
    previous_due = deadline.due_at if deadline else course.deadline_at
    if deadline is None:
        deadline = GroupCourseDeadline(group_id=group_id, course_id=course_id)
        db.add(deadline)
    deadline.due_at = data.due_at
    deadline.set_by = user.id
    await db.flush()
    await db.refresh(deadline)
    await _notify_changed_deadline(db, group_id, course_id, None, before, previous_due)
    return CourseDeadlineState(
        own=OwnDeadline.model_validate(deadline), effective_due_at=deadline.due_at
    )


@deadlines.delete("/{group_id}/courses/{course_id}/deadline", status_code=204)
@access_note("Куратор — только для своей группы, администратор — для любой.")
async def delete_course_deadline(
    group_id: int,
    course_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    await courses_svc.get_course(db, course_id)
    deadline = await db.scalar(
        select(GroupCourseDeadline).where(
            GroupCourseDeadline.group_id == group_id,
            GroupCourseDeadline.course_id == course_id,
        )
    )
    if deadline is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deadline not found")
    before = await effective_deadlines(db, group_id, course_id)
    previous_due = deadline.due_at
    await db.delete(deadline)
    await db.flush()
    await _notify_changed_deadline(db, group_id, course_id, None, before, previous_due)


@deadlines.get(
    "/{group_id}/courses/{course_id}/deadlines", response_model=list[StepDeadline]
)
@access_note(
    "Куратор — только для своей группы, администратор — для любой. Все видимые "
    "шаги курса по порядку: дедлайн, выставленный на шаге (`own`), и итоговый, "
    "который видят ученики (`effective`), с дедлайном курса как запасным."
)
async def course_deadlines(
    group_id: int,
    course_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    await courses_svc.get_course(db, course_id)
    effective = await effective_deadlines(db, group_id, course_id)
    order = [s.id for s in await courses_svc.visible_steps_in_order(db, course_id)]
    steps = {
        step.id: (step, content)
        for step, content in await db.execute(
            select(Step, StepRevision.content)
            .join(StepRevision, StepRevision.id == Step.current_revision_id)
            .where(Step.id.in_(order))
        )
    }
    modules = {
        module.id: module
        for module in await db.scalars(
            select(Module).where(
                Module.id.in_({step.module_id for step, _ in steps.values()})
            )
        )
    }
    own = {
        d.step_id: d
        for d in await db.scalars(
            select(Deadline).where(
                Deadline.group_id == group_id, Deadline.step_id.in_(order)
            )
        )
    }
    return [
        StepDeadline(
            step_id=step_id,
            module_id=steps[step_id][0].module_id,
            module_title=modules[steps[step_id][0].module_id].title,
            module_position=modules[steps[step_id][0].module_id].position,
            step_position=steps[step_id][0].position,
            title=courses_svc.get_step_title(steps[step_id][1]),
            type=steps[step_id][0].type,
            own=OwnDeadline.model_validate(own[step_id]) if step_id in own else None,
            effective=view(step_id, effective.get(step_id)),
        )
        for step_id in order
    ]


@deadlines.put("/{group_id}/deadlines/{step_id}", response_model=OwnDeadline)
@access_note(
    "Куратор — только для своей группы, администратор — для любой. Задаёт или "
    "заменяет дедлайн шага для группы; шаги перед ним без своего дедлайна "
    "получают этот же."
)
async def set_deadline(
    group_id: int,
    step_id: int,
    data: DeadlineIn,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    step = await _live_step(db, step_id)
    module = await db.get(Module, step.module_id)
    before = await effective_deadlines(db, group_id, module.course_id)
    deadline = await db.scalar(
        select(Deadline).where(
            Deadline.group_id == group_id, Deadline.step_id == step_id
        )
    )
    if deadline is None:
        deadline = Deadline(group_id=group_id, step_id=step_id)
        db.add(deadline)
    deadline.due_at = data.due_at
    deadline.set_by = user.id
    await db.flush()
    await db.refresh(deadline)
    await _notify_changed_deadline(db, group_id, module.course_id, step_id, before)
    return deadline


@deadlines.delete("/{group_id}/deadlines/{step_id}", status_code=204)
@access_note("Куратор — только для своей группы, администратор — для любой.")
async def delete_deadline(
    group_id: int,
    step_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    deadline = await db.scalar(
        select(Deadline).where(
            Deadline.group_id == group_id, Deadline.step_id == step_id
        )
    )
    if deadline is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deadline not found")
    step = await db.get(Step, step_id)
    module = await db.get(Module, step.module_id)
    before = await effective_deadlines(db, group_id, module.course_id)
    await db.delete(deadline)
    await db.flush()
    await _notify_changed_deadline(db, group_id, module.course_id, step_id, before)
