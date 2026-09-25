from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import get_current_user, require_curator
from courses import service as courses_svc
from courses.models import Course
from database import access_db
from groups.service import group_students, manageable_group, student_group_id
from models import User
from progress.rating import group_rating, my_rating
from progress.schemas import (
    CourseProgressOut,
    ModuleProgress,
    MyRating,
    RatingRow,
    StudentProgressRow,
)
from progress.service import course_progress

progress_api = APIRouter(tags=["progress"])


async def published_course(db: AsyncSession, course_id: int) -> Course:
    course = await courses_svc.get_course(db, course_id)
    if not course.is_published:
        raise courses_svc.not_found("Course")
    return course


@progress_api.get("/courses/{course_id}/progress", response_model=CourseProgressOut)
@access_note(
    "Только свой прогресс и только по опубликованному курсу. Пройдено шагов, "
    "набрано баллов, итоги по модулям, разбивка по каждому шагу (за что и кем "
    "начислены баллы) и следующий шаг. Правила подсчёта — в README, раздел "
    "«Прогресс»."
)
async def my_progress(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    course = await published_course(db, course_id)
    progress = (await course_progress(db, course, [user]))[user.id]
    modules = await courses_svc.live_modules(db, course.id)
    return CourseProgressOut(
        **progress.summary().model_dump(),
        course_id=course.id,
        modules=[
            ModuleProgress(
                module_id=m.id,
                title=m.title,
                **progress.module_totals(m.id).model_dump(),
            )
            for m in modules
        ],
        steps=[r.as_detail() for r in progress.steps],
    )


@progress_api.get(
    "/groups/{group_id}/courses/{course_id}/progress",
    response_model=list[StudentProgressRow],
)
@access_note(
    "Куратор — только для своей группы, администратор — для любой. Итог "
    "каждого ученика группы по курсу; подробности по ученику — в очереди "
    "проверки."
)
async def group_progress(
    group_id: int,
    course_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    course = await courses_svc.get_course(db, course_id)
    students = await group_students(db, group_id)
    progress = await course_progress(db, course, students)
    return [
        StudentProgressRow(
            student_id=s.id, username=s.username, progress=progress[s.id].summary()
        )
        for s in students
    ]


@progress_api.get("/courses/{course_id}/rating", response_model=MyRating)
@access_note(
    "Только свои данные: баллы, место в группе и обезличенные цели — сколько "
    "баллов у ближайшего места выше и у первого места, сколько нужно набрать "
    "(больше `gap`), чтобы их обойти, и в каких шагах эти баллы взять. Без "
    "группы рейтинга нет (404). Формула и правила — в README, раздел «Рейтинг»."
)
async def get_my_rating(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    course = await published_course(db, course_id)
    group_id = await student_group_id(db, user)
    if group_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not in a group")
    rating = await group_rating(db, course, await group_students(db, group_id))
    return await my_rating(db, course, user, rating)


@progress_api.get(
    "/groups/{group_id}/courses/{course_id}/rating", response_model=list[RatingRow]
)
@access_note(
    "Куратор — только для своей группы, администратор — для любой. Рейтинг "
    "группы по курсу с именами, по местам."
)
async def get_group_rating(
    group_id: int,
    course_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    course = await courses_svc.get_course(db, course_id)
    rating = await group_rating(db, course, await group_students(db, group_id))
    return rating.rows()
