import enum

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models import BaseDB, User


class FilePurpose(enum.StrEnum):
    CONTENT = "content"  # course materials, readable by any signed-in user
    SUBMISSION = "submission"  # student's attachment, private
    # Hidden tests, reference answers: admins and curators only.
    ANSWER_KEY = "answer_key"


class FileStatus(enum.StrEnum):
    PENDING = "pending"  # upload URL issued, upload not confirmed yet
    READY = "ready"


def _enum(e: type[enum.Enum]) -> Enum:
    return Enum(
        e, native_enum=False, length=16, values_callable=lambda x: [v.value for v in x]
    )


class File(BaseDB):
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), index=True
    )
    purpose: Mapped[FilePurpose] = mapped_column(_enum(FilePurpose))
    status: Mapped[FileStatus] = mapped_column(
        _enum(FileStatus), default=FileStatus.PENDING
    )
    storage_key: Mapped[str] = mapped_column(String(200), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(127))
    size: Mapped[int] = mapped_column(BigInteger)
