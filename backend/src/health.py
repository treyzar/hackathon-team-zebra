from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import text

from database import access_db

health = APIRouter(prefix="/health")


@health.get("")
async def check_health(db=Depends(access_db)):
    try:
        await db.scalar(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DB dead :("
        )
    return {"status": "ok"}
