from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import all_models  # noqa: F401  # register every mapper
from admin import admin
from auth import auth, get_current_user, require_auth
from config import settings
from courses.admin_api import authoring
from courses.student_api import learning
from files.api import files
from groups.api import groups
from health import health
from schemas import UserResponse
from submissions.review_api import review

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
api.include_router(groups)
api.include_router(authoring)
api.include_router(learning)
api.include_router(review)
api.include_router(files)
app.include_router(health)


@app.get("/whoami")  # test route
async def whoami(user_id=Depends(require_auth)):
    return {"user_id": user_id}


@api.get("/user/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)) -> UserResponse:
    return user


app.include_router(api)
