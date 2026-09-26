from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import get_current_user, require_curator, require_roles
from courses import service as courses_svc
from courses.access import ensure_enrolled
from courses.models import Course
from database import access_db
from groups.models import Group
from groups.service import group_students, manageable_group, student_group_id
from models import Role, User
from progress.analytics import course_analytics, module_analytics
from progress.lag import LagStatus, group_lag, students_lag, worst
from progress.rating import my_rating, rating_of
from progress.schemas import (
    CourseAnalytics,
    CourseProgressOut,
    Learner,
    LearnerCourse,
    LearnerGroup,
    ModuleAnalytics,
    ModuleProgress,
    MyRating,
    RatingRow,
    StudentLagRow,
    StudentProgressRow,
)
from progress.service import course_progress

progress_api = APIRouter(tags=["progress"])
require_student = require_roles(Role.STUDENT)


async def student_course(db: AsyncSession, course_id: int, user: User) -> Course:
    """A published course the user is enrolled in (staff: any published)."""
    course = await courses_svc.get_course(db, course_id)
    if not course.is_published:
        raise courses_svc.not_found("Course")
    await ensure_enrolled(db, user, course.id)
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
    course = await student_course(db, course_id, user)
    progress = (await course_progress(db, course, [user]))[user.id]
    modules = await courses_svc.live_modules(db, course.id)
    group_id = await student_group_id(db, user)
    lag = (await group_lag(db, course, group_id, {user.id: progress}))[user.id]
    return CourseProgressOut(
        **progress.summary().model_dump(),
        course_id=course.id,
        lag=lag,
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
    students = await group_students(db, group_id, course.id)
    progress = await course_progress(db, course, students)
    lag = await group_lag(db, course, group_id, progress)
    return [
        StudentProgressRow(
            student_id=s.id,
            username=s.username,
            progress=progress[s.id].summary(),
            lag=lag[s.id],
        )
        for s in students
    ]


_SEVERITY = {LagStatus.FALLING_BEHIND: 0, LagStatus.SLOWED: 1}


@progress_api.get(
    "/groups/{group_id}/courses/{course_id}/lagging",
    response_model=list[StudentLagRow],
)
@access_note(
    "Куратор — только для своей группы, администратор — для любой. Только "
    "отстающие: сначала «выпадает» (просрочка больше недели), затем "
    "«замедлился»; внутри — по самой давней просрочке. У каждого — причина: "
    "просроченные шаги и их состояние. Правило — в README, раздел «Отставание»."
)
async def lagging_students(
    group_id: int,
    course_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    course = await courses_svc.get_course(db, course_id)
    students = await group_students(db, group_id, course.id)
    lag = await group_lag(
        db, course, group_id, await course_progress(db, course, students)
    )
    rows = [
        StudentLagRow(student_id=s.id, username=s.username, lag=lag[s.id])
        for s in students
        if lag[s.id].status != LagStatus.ON_TRACK
    ]
    return sorted(
        rows,
        key=lambda r: (_SEVERITY[r.lag.status], r.lag.overdue[0].due_at, r.username),
    )


@progress_api.get("/rating", response_model=MyRating)
@access_note(
    "Только ученик и только свои данные: итог и его составляющие (баллы по "
    "каждому своему курсу и бонус за серию), место в группе и обезличенные "
    "цели — рейтинг ближайшего места выше и первого места, сколько нужно "
    "набрать (больше `gap`), чтобы их обойти, и в каких шагах эти баллы "
    "взять. Без группы — только итог и составляющие. Правила — в README, "
    "раздел «Рейтинг»."
)
async def get_my_rating(
    user: User = Depends(require_student),
    db: AsyncSession = Depends(access_db),
):
    group_id = await student_group_id(db, user)
    students = await group_students(db, group_id) if group_id else [user]
    return await my_rating(
        db, user, await rating_of(db, students), in_group=group_id is not None
    )


@progress_api.get("/groups/{group_id}/rating", response_model=list[RatingRow])
@access_note(
    "Куратор — только для своей группы, администратор — для любой. Рейтинг "
    "группы по местам: имена, итог, баллы по каждому курсу ученика и бонус за "
    "серию."
)
async def get_group_rating(
    group_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    await manageable_group(db, user, group_id)
    rating = await rating_of(db, await group_students(db, group_id))
    return rating.rows()


ANALYTICS_ACCESS = (
    "Куратор — только для своей группы, администратор — для любой. Считаются "
    "ученики группы, записанные на курс. Определения — в README, раздел "
    "«Аналитика»."
)


@progress_api.get(
    "/groups/{group_id}/courses/{course_id}/analytics",
    response_model=CourseAnalytics,
)
@access_note(ANALYTICS_ACCESS)
async def group_course_analytics(
    group_id: int,
    course_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    """Аналитика группы по курсу. По каждому модулю: сколько учеников его
    прошли, в процессе и не начинали; процент решений с первой попытки;
    среднее число попыток на задание; число возвратов с ручной проверки.
    По каждому ученику: пройдено шагов в каждом модуле, есть ли решения по
    задачам модуля и необработанный возврат; отставание от графика; время
    последней отправки."""
    await manageable_group(db, user, group_id)
    course = await courses_svc.get_course(db, course_id)
    students = await group_students(db, group_id, course.id)
    return await course_analytics(db, course, group_id, students)


@progress_api.get(
    "/groups/{group_id}/courses/{course_id}/modules/{module_id}/analytics",
    response_model=ModuleAnalytics,
)
@access_note(ANALYTICS_ACCESS)
async def group_module_analytics(
    group_id: int,
    course_id: int,
    module_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    """Подробно по модулю: шаги (номер, тип, название, максимум) и результат
    каждого ученика группы по каждому шагу — состояние, баллы, число
    попыток, решён ли с первой попытки, необработанный возврат, последняя
    отправка. Плюс сводка модуля, как в аналитике курса."""
    await manageable_group(db, user, group_id)
    course = await courses_svc.get_course(db, course_id)
    module = next(
        (m for m in await courses_svc.live_modules(db, course.id) if m.id == module_id),
        None,
    )
    if module is None:
        raise courses_svc.not_found("Module")
    students = await group_students(db, group_id, course.id)
    return await module_analytics(db, course, module, students)


@progress_api.get("/learners", response_model=list[LearnerGroup])
@access_note(
    "Куратор — свои группы, администратор — все. Группы с учениками: у каждого "
    "ученика статус по каждому его курсу (правило — в README, раздел "
    "«Отставание») и итоговый — худший из них."
)
async def list_learners(
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    """Ученики курируемых групп и их статус: «в графике», «замедлился» или
    «выпадает» — худший по курсам, на которые ученик записан."""
    query = select(Group).order_by(Group.name)
    if user.role != Role.ADMIN:
        query = query.where(Group.curator_id == user.id)
    result = []
    for group in await db.scalars(query):
        students = await group_students(db, group.id)
        lag = await students_lag(db, group.id, students)
        result.append(
            LearnerGroup(
                group_id=group.id,
                name=group.name,
                students=[
                    Learner(
                        student_id=s.id,
                        username=s.username,
                        name=s.name,
                        surname=s.surname,
                        patronymic=s.patronymic,
                        status=worst([value.status for _, value in lag[s.id]]),
                        courses=[
                            LearnerCourse(
                                course_id=course.id,
                                title=course.title,
                                status=value.status,
                                overdue_steps=len(value.overdue),
                            )
                            for course, value in lag[s.id]
                        ],
                    )
                    for s in students
                ],
            )
        )
    return result
