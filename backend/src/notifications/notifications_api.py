from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import get_current_user
from database import access_db
from models import User
from notifications import service
from notifications.schemas import NotificationOut, UnreadCount

notifications = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications.get("", response_model=list[NotificationOut])
@access_note("Только свои уведомления.")
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    return await service.list_for_user(
        db, user.id, unread_only=unread_only, limit=limit, offset=offset
    )


@notifications.get("/unread_count", response_model=UnreadCount)
@access_note("Только свои уведомления.")
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    return UnreadCount(count=await service.unread_count(db, user.id))


@notifications.post("/{notification_id}/read", response_model=NotificationOut)
@access_note("Только своё уведомление.")
async def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    from fastapi import HTTPException, status

    n = await service.mark_read(db, user.id, notification_id)
    if n is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    return n


@notifications.post("/read_all", response_model=UnreadCount)
@access_note("Только свои уведомления.")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    await service.mark_all_read(db, user.id)
    return UnreadCount(count=0)
