from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from files.models import FilePurpose

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_FILENAME = "manifest.json"
COURSE_DOCUMENT_FILENAME = "course.json"
ARCHIVED_FILES_PREFIX = "files/"


class ManifestFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(gt=0)
    path: str = Field(min_length=1, max_length=1024)
    purpose: FilePurpose
    filename: str = Field(min_length=1, max_length=255)
    mime: str = Field(min_length=1, max_length=127, pattern=r"^[\w.+-]+/[\w.+-]+$")
    size: int = Field(gt=0)

    @field_validator("path")
    @classmethod
    def _safe_path(cls, value: str) -> str:
        if value.startswith("/"):
            raise ValueError("Archive paths must be relative")
        if "\\" in value:
            raise ValueError("Archive paths use forward slashes only")
        if "\x00" in value:
            raise ValueError("Archive paths cannot contain NUL")
        if any(part in ("", ".", "..") for part in value.split("/")):
            raise ValueError("Archive paths cannot contain '.', '..' or empty segments")
        return value

    @field_validator("filename")
    @classmethod
    def _plain_filename(cls, value: str) -> str:
        if "/" in value or "\\" in value:
            raise ValueError("Filename cannot contain path separators")
        if "\x00" in value:
            raise ValueError("Filename cannot contain NUL")
        return value


class ArchiveManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[MANIFEST_SCHEMA_VERSION] = MANIFEST_SCHEMA_VERSION
    files: list[ManifestFile] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self):
        ids = [f.id for f in self.files]
        if len(set(ids)) != len(ids):
            raise ValueError("File ids in the manifest must be unique")
        paths = [f.path for f in self.files]
        if len(set(paths)) != len(paths):
            raise ValueError("Archive paths must be unique")
        return self

    def by_id(self) -> dict[int, ManifestFile]:
        return {f.id: f for f in self.files}

    def paths(self) -> set[str]:
        return {f.path for f in self.files}
