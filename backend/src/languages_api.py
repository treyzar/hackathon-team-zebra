from functools import cache

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_auth
from judge import JudgeClient, JudgeError
from languages import LANGUAGES

programming_languages = APIRouter(
    prefix="/programming", tags=["programming"], dependencies=[Depends(require_auth)]
)


class LanguageInfo(BaseModel):
    key: str
    title: str
    # Whether the Judge0 server offers the language right now; null when Judge0
    # could not be asked. Steps may still allow an unavailable language: only
    # its checking fails, nothing else.
    available: bool | None


@cache
def _judge() -> JudgeClient:
    # Lives as long as the process; it caches Judge0's language list.
    return JudgeClient()


@programming_languages.get("/languages")
async def list_languages() -> list[LanguageInfo]:
    """Languages a programming step can allow, for the authoring form."""
    try:
        ids = await _judge().language_ids()
    except JudgeError:
        ids = None
    return [
        LanguageInfo(
            key=key,
            title=spec.title,
            available=None if ids is None else key in ids,
        )
        for key, spec in LANGUAGES.items()
    ]
