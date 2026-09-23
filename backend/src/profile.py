from fastapi import APIRouter, Depends

from auth import require_auth

profile = APIRouter(dependencies=[Depends(require_auth)])
