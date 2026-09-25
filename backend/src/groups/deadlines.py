"""Deadlines of steps, per group.

A curator (for their own groups) or an admin sets a deadline on a step. A step
without its own deadline gets the deadline of the nearest following step that
has one: set a deadline on the last step of a topic and every step before it
shares it. Only the deadlines people set are stored; inherited ones are
computed when shown, so the two are always told apart.
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
from courses.models import Module, Step
from courses.schemas import DeadlineView
from database import access_db
from groups.models import Deadline, Group, GroupStudent
from models import Role, User

deadlines = APIRouter(prefix="/groups", tags=["deadlines"])


@dataclass
class Effective:
    due_at: datetime
    # The step whose deadline this is; equals the step itself unless inherited.
    source_step_id: int


async def effective_deadlines(
    db: AsyncSession, group_id: int | None, course_id: int
) -> dict[int, Effective]:
    """Deadline of every visible step of the course for the group, own or
    inherited from the nearest following step. Steps after the last deadline
    have none."""
    if group_id is None:
        return {}
    order = [
        step_id
        for step_id, _ in await courses_svc.visible_steps_in_order(db, course_id)
    ]
    own = dict(
        (
            await db.execute(
                select(Deadline.step_id, Deadline.due_at).where(
                    Deadline.group_id == group_id, Deadline.step_id.in_(order)
                )
            )
        ).all()
    )
    result: dict[int, Effective] = {}
    carry: Effective | None = None
    for step_id in reversed(order):
        if step_id in own:
            carry = Effective(own[step_id], step_id)
        if carry is not None:
            result[step_id] = carry
    return result


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
    per_course: dict[tuple[int, int], dict[int, Effective]] = {}
    result: dict[int, datetime | None] = {}
    for s in subs:
        key = (groups.get(s.user_id), courses.get(s.step_id))
        if None in key:
            result[s.id] = None
            continue
        if key not in per_course:
            per_course[key] = await effective_deadlines(db, *key)
        eff = per_course[key].get(s.step_id)
        result[s.id] = eff.due_at if eff else None
    return result


def is_late(sub, due_at: datetime | None) -> bool:
    return due_at is not None and sub.created_at > due_at


async def student_group_id(db: AsyncSession, user: User) -> int | None:
    membership = await db.get(GroupStudent, user.id)
    return membership.group_id if membership else None


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
    type: str
    # What a person set on this step, if anything.
    own: OwnDeadline | None
    # What students see: own or inherited.
    effective: DeadlineView | None


def view(step_id: int, eff: Effective | None) -> DeadlineView | None:
    if eff is None:
        return None
    return DeadlineView(
        due_at=eff.due_at,
        inherited=eff.source_step_id != step_id,
        source_step_id=eff.source_step_id,
    )


async def _manageable_group(db: AsyncSession, user: User, group_id: int) -> Group:
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    if user.role != Role.ADMIN and group.curator_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your group")
    return group


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


@deadlines.get(
    "/{group_id}/courses/{course_id}/deadlines", response_model=list[StepDeadline]
)
@access_note(
    "Куратор — только для своей группы, администратор — для любой. Все видимые "
    "шаги курса по порядку: дедлайн, выставленный на шаге (`own`), и итоговый, "
    "который видят ученики (`effective`)."
)
async def course_deadlines(
    group_id: int,
    course_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await _manageable_group(db, user, group_id)
    await courses_svc.get_course(db, course_id)
    effective = await effective_deadlines(db, group_id, course_id)
    order = [s for s, _ in await courses_svc.visible_steps_in_order(db, course_id)]
    steps = {s.id: s for s in await db.scalars(select(Step).where(Step.id.in_(order)))}
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
            module_id=steps[step_id].module_id,
            type=steps[step_id].type,
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
    await _manageable_group(db, user, group_id)
    await _live_step(db, step_id)
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
    return deadline


@deadlines.delete("/{group_id}/deadlines/{step_id}", status_code=204)
@access_note("Куратор — только для своей группы, администратор — для любой.")
async def delete_deadline(
    group_id: int,
    step_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await _manageable_group(db, user, group_id)
    deadline = await db.scalar(
        select(Deadline).where(
            Deadline.group_id == group_id, Deadline.step_id == step_id
        )
    )
    if deadline is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deadline not found")
    await db.delete(deadline)
