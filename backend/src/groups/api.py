from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_admin
from database import access_db
from groups.models import Group, GroupStudent
from models import Role, User
from schemas import UserResponse

groups = APIRouter(
    prefix="/admin/groups", tags=["groups"], dependencies=[Depends(require_admin)]
)


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    curator_id: int | None = None


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    curator_id: int | None = None


class GroupOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    curator_id: int | None
    students_count: int = 0


async def _get_group(db: AsyncSession, group_id: int) -> Group:
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    return group


async def _check_user_role(db: AsyncSession, user_id: int, role: Role) -> User:
    user = await db.get(User, user_id)
    if not user or user.role != role:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"User {user_id} is not a {role}"
        )
    return user


async def _out(db: AsyncSession, group: Group) -> GroupOut:
    count = await db.scalar(
        select(func.count()).where(GroupStudent.group_id == group.id)
    )
    return GroupOut(
        id=group.id, name=group.name, curator_id=group.curator_id, students_count=count
    )


async def _flush_unique(db: AsyncSession) -> None:
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "Group name is taken") from e


@groups.get("", response_model=list[GroupOut])
async def list_groups(db: AsyncSession = Depends(access_db)):
    counts = (
        select(GroupStudent.group_id, func.count().label("n"))
        .group_by(GroupStudent.group_id)
        .subquery()
    )
    rows = await db.execute(
        select(Group, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.group_id == Group.id)
        .order_by(Group.name)
    )
    return [
        GroupOut(id=g.id, name=g.name, curator_id=g.curator_id, students_count=n)
        for g, n in rows
    ]


@groups.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(data: GroupCreate, db: AsyncSession = Depends(access_db)):
    if data.curator_id is not None:
        await _check_user_role(db, data.curator_id, Role.CURATOR)
    group = Group(name=data.name, curator_id=data.curator_id)
    db.add(group)
    await _flush_unique(db)
    return await _out(db, group)


@groups.patch("/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: int, data: GroupUpdate, db: AsyncSession = Depends(access_db)
):
    group = await _get_group(db, group_id)
    if data.name is not None:
        group.name = data.name
    if "curator_id" in data.model_fields_set:
        if data.curator_id is not None:
            await _check_user_role(db, data.curator_id, Role.CURATOR)
        group.curator_id = data.curator_id
    await _flush_unique(db)
    return await _out(db, group)


@groups.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: int, db: AsyncSession = Depends(access_db)):
    await db.delete(await _get_group(db, group_id))


@groups.get("/{group_id}/students", response_model=list[UserResponse])
async def list_students(group_id: int, db: AsyncSession = Depends(access_db)):
    await _get_group(db, group_id)
    query = (
        select(User)
        .join(GroupStudent, GroupStudent.user_id == User.id)
        .where(GroupStudent.group_id == group_id)
        .order_by(User.username)
    )
    return (await db.scalars(query)).all()


@groups.put("/{group_id}/students/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_student(
    group_id: int, user_id: int, db: AsyncSession = Depends(access_db)
):
    """Put the student into the group, moving them out of their previous one."""
    await _get_group(db, group_id)
    await _check_user_role(db, user_id, Role.STUDENT)
    membership = await db.get(GroupStudent, user_id)
    if membership:
        membership.group_id = group_id
    else:
        db.add(GroupStudent(user_id=user_id, group_id=group_id))


@groups.delete("/{group_id}/students/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_student(
    group_id: int, user_id: int, db: AsyncSession = Depends(access_db)
):
    membership = await db.get(GroupStudent, user_id)
    if not membership or membership.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student is not in this group")
    await db.delete(membership)
