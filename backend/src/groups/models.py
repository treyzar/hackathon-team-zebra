from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models import BaseDB, User


class Group(BaseDB):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    curator_id: Mapped[int | None] = mapped_column(
        ForeignKey(User.id, ondelete="SET NULL"), index=True
    )


class GroupStudent(BaseDB):
    # A student belongs to at most one group, hence user_id is the key.
    user_id: Mapped[int] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey(Group.id, ondelete="CASCADE"), index=True
    )
