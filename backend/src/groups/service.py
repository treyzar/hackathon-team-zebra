from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from groups.models import Group, GroupStudent
from models import Role, User


def students_of_curator(curator_id: int) -> Select[tuple[int]]:
    """Ids of students in groups the curator is assigned to (current membership)."""
    return (
        select(GroupStudent.user_id)
        .join(Group, Group.id == GroupStudent.group_id)
        .where(Group.curator_id == curator_id)
    )


async def can_see_student(db: AsyncSession, viewer: User, student_id: int) -> bool:
    """Whether ``viewer`` may see the student's submissions and files."""
    if viewer.role == Role.ADMIN or viewer.id == student_id:
        return True
    if viewer.role != Role.CURATOR:
        return False
    query = students_of_curator(viewer.id).where(GroupStudent.user_id == student_id)
    return await db.scalar(query) is not None


async def detach_on_role_change(db: AsyncSession, user: User) -> None:
    """Keep group links consistent with the user's (new) role."""
    if user.role != Role.CURATOR:
        for group in await db.scalars(select(Group).where(Group.curator_id == user.id)):
            group.curator_id = None
    if user.role != Role.STUDENT:
        membership = await db.get(GroupStudent, user.id)
        if membership:
            await db.delete(membership)


async def manageable_group(db: AsyncSession, user: User, group_id: int) -> Group:
    """The group, if the user may manage it: admins any, curators their own."""
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    if user.role != Role.ADMIN and group.curator_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your group")
    return group


async def student_group_id(db: AsyncSession, user: User) -> int | None:
    membership = await db.get(GroupStudent, user.id)
    return membership.group_id if membership else None


async def group_students(db: AsyncSession, group_id: int) -> list[User]:
    """Current students of the group, by username."""
    query = (
        select(User)
        .join(GroupStudent, GroupStudent.user_id == User.id)
        .where(GroupStudent.group_id == group_id)
        .order_by(User.username)
    )
    return list(await db.scalars(query))
