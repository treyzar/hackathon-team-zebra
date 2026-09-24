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
