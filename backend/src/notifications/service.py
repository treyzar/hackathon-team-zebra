from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from courses.service import now
from notifications.models import Notification, NotificationType, Severity

async def mark_read(
    db: AsyncSession, user_id: int, notification_id: int
) -> Notification | None:
    notification = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    if notification and notification.read_at is None:
        notification.read_at = now()
    return notification

async def unread_count(db: AsyncSession, user_id: int) -> int:
    count = await db.scalar(
        select(func.count()).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    )
    return count or 0

async def list_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    query = query.order_by(Notification.id.desc()).limit(limit).offset(offset)
    return list(await db.scalars(query))