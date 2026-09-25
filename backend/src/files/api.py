"""Direct-to-storage uploads: the client asks for a presigned URL, PUTs the file
to it, then confirms the upload."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import get_current_user
from config import settings
from database import access_db
from files import storage
from files.models import File, FilePurpose, FileStatus
from groups.service import can_see_student
from models import Role, User

files = APIRouter(prefix="/files", tags=["files"])


class UploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime: str = Field(pattern=r"^[\w.+-]+/[\w.+-]+$", max_length=127)
    size: int = Field(gt=0)
    purpose: FilePurpose


class FileOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    filename: str
    mime: str
    size: int
    purpose: FilePurpose
    status: FileStatus


class UploadTicket(FileOut):
    upload_url: str
    # Headers the client must send with the PUT request.
    upload_headers: dict[str, str]


class DownloadOut(FileOut):
    download_url: str


# Purposes only admins may upload.
ADMIN_PURPOSES = {FilePurpose.CONTENT, FilePurpose.ANSWER_KEY}


async def can_read(db: AsyncSession, user: User, file: File) -> bool:
    match file.purpose:
        case FilePurpose.CONTENT:
            return True
        case FilePurpose.ANSWER_KEY:
            return user.role in (Role.ADMIN, Role.CURATOR)
    return await can_see_student(db, user, file.owner_id)


async def _get(db: AsyncSession, file_id: int) -> File:
    file = await db.get(File, file_id)
    if not file:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return file


@files.post("", response_model=UploadTicket, status_code=status.HTTP_201_CREATED)
@access_note(
    "Файлы с `purpose` `content` и `answer_key` загружает только администратор, "
    "`submission` — любой вошедший пользователь."
)
async def request_upload(
    data: UploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    if data.purpose in ADMIN_PURPOSES and user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins upload materials")
    if data.size > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"File is larger than {settings.max_upload_mb} MB",
        )
    file = File(
        owner_id=user.id,
        purpose=data.purpose,
        status=FileStatus.PENDING,
        storage_key=f"{data.purpose}/{uuid4().hex}",
        filename=data.filename,
        mime=data.mime,
        size=data.size,
    )
    db.add(file)
    await db.flush()
    return UploadTicket(
        **FileOut.model_validate(file).model_dump(),
        upload_url=storage.presign_upload(file.storage_key, file.mime),
        upload_headers={"Content-Type": file.mime},
    )


@files.post("/{file_id}/complete", response_model=FileOut)
@access_note("Только владелец файла — тот, кто запросил загрузку.")
async def complete_upload(
    file_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    file = await _get(db, file_id)
    if file.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    if file.status == FileStatus.READY:
        return file
    size = await storage.object_size(file.storage_key)
    if size is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "File has not been uploaded")
    if size != file.size:
        raise HTTPException(status.HTTP_409_CONFLICT, "Uploaded size does not match")
    file.status = FileStatus.READY
    return file


@files.get("/{file_id}", response_model=DownloadOut)
@access_note(
    "`content` — любой вошедший пользователь; `answer_key` — кураторы и "
    "администраторы; `submission` — владелец, куратор его группы и администраторы."
)
async def get_file(
    file_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    file = await _get(db, file_id)
    if file.status != FileStatus.READY or not await can_read(db, user, file):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return DownloadOut(
        **FileOut.model_validate(file).model_dump(),
        download_url=storage.presign_download(file.storage_key, file.filename),
    )
