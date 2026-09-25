from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import all_models  # noqa: F401  # register every mapper
from access_docs import document_access
from admin import admin
from auth import auth, get_current_user, require_auth
from config import settings
from courses.admin_api import authoring
from courses.student_api import learning
from files.api import files
from groups.api import groups
from groups.deadlines import deadlines
from health import health
from notifications.notifications_api import notifications
from progress.api import progress_api
from schemas import UserResponse
from submissions.review_api import review

app = FastAPI(
    title="Sasha",
    description=(
        "Роли: **ученик** (по умолчанию после регистрации), **куратор**, "
        "**администратор**. У каждого эндпоинта указано, кому он доступен.\n\n"
        "Авторизация: кнопка **Authorize** — войти логином и паролем, токен "
        "подставится во все запросы."
    ),
)
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
api.include_router(deadlines)
api.include_router(authoring)
api.include_router(learning)
api.include_router(progress_api)
api.include_router(review)
api.include_router(files)
api.include_router(notifications)
app.include_router(health)


@app.get("/whoami")  # test route
async def whoami(user_id=Depends(require_auth)):
    return {"user_id": user_id}


@api.get("/user/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)) -> UserResponse:
    return user


app.include_router(api)
# Who may call each endpoint, shown in /docs.
document_access(app)
