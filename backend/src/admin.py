from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import require_admin
from database import access_db
from groups.service import detach_on_role_change
from models import Role, User
from schemas import RoleUpdate, UserResponse

admin = APIRouter(prefix="/admin", tags=["admin"])


@admin.get("/users", response_model=list[UserResponse])
async def list_users(
    role: Role | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(access_db),
):
    query = select(User).order_by(User.id)
    if role:
        query = query.where(User.role == role)
    return (await db.scalars(query)).all()


@admin.patch("/users/{user_id}/role", response_model=UserResponse)
@access_note(
    "Свою роль изменить нельзя. При смене роли пользователь отвязывается от групп, "
    "где новая роль не подходит (куратор группы, ученик в группе)."
)
async def set_role(
    user_id: int,
    data: RoleUpdate,
    current: User = Depends(require_admin),
    db: AsyncSession = Depends(access_db),
):
    if user_id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot change their own role",
        )
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    user.role = data.role
    await detach_on_role_change(db, user)
    await db.flush()
    return user
