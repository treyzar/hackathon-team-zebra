from datetime import datetime
from typing import Any

from pydantic import BaseModel

from notifications.models import NotificationType, Severity


class NotificationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    type: NotificationType
    severity: Severity
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class UnreadCount(BaseModel):
    count: int
