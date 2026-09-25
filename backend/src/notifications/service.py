from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from courses.service import now
from notifications.models import Notification, NotificationType, Severity
from notifications.payloads import PAYLOADS


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: NotificationType,
    payload: BaseModel | None = None,
    *,
    severity: Severity = Severity.INFO,
    dedup_key: str | None = None,
) -> None:
    data: dict[str, Any] = {} if payload is None else payload.model_dump(mode="json")
    if model := PAYLOADS.get(type):
        data = model.model_validate(data).model_dump(mode="json")
    values = {
        "user_id": user_id,
        "type": type.value,
        "severity": severity.value,
        "payload": data,
        "dedup_key": dedup_key,
    }
    query = pg_insert(Notification).values(**values)
    if dedup_key is not None:
        query = query.on_conflict_do_nothing(index_elements=["user_id", "dedup_key"])
    await db.execute(query)


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


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now())
    )
    return result.rowcount or 0


async def unread_count(db: AsyncSession, user_id: int) -> int:
    return (
        await db.scalar(
            select(func.count()).where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )


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
