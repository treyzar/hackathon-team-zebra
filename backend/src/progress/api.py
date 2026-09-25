from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import get_current_user, require_curator
from courses import service as courses_svc
from courses.models import Course
from database import access_db
from groups.models import GroupStudent
from groups.service import manageable_group
from models import User
from progress.schemas import CourseProgressOut, ModuleProgress, StudentProgressRow
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
    students = list(
        await db.scalars(
            select(User)
            .join(GroupStudent, GroupStudent.user_id == User.id)
            .where(GroupStudent.group_id == group_id)
            .order_by(User.username)
        )
    )
    progress = await course_progress(db, course, students)
    return [
        StudentProgressRow(
            student_id=s.id, username=s.username, progress=progress[s.id].summary()
        )
        for s in students
    ]
