from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin import admin
from auth import auth, get_current_user, require_auth
from config import settings
from health import health
from schemas import UserResponse

app = FastAPI(title="Sasha")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api", tags=["api"])
api.include_router(auth)
api.include_router(admin)
app.include_router(health)


@app.get("/whoami")  # test route
async def whoami(user_id=Depends(require_auth)):
    return {"user_id": user_id}


@api.get("/user/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)) -> UserResponse:
    return user


app.include_router(api)
