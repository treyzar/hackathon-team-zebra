from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import get_current_user
from courses import service as svc
from courses.access import (
    enrolled_course_ids,
    ensure_enrolled,
    ensure_unlocked,
    locked_steps,
)
from courses.models import Course, Step, StepRevision
from courses.schemas import (
    StudentCourse,
    StudentCourseListItem,
    StudentModule,
    StudentStep,
    StudentStepSummary,
    SubmissionOut,
    SubmitIn,
)
from database import access_db
from groups.deadlines import (
    effective_deadlines,
    is_late,
    submission_deadlines,
)
from groups.deadlines import view as deadline_view
from groups.service import student_group_id
from models import Role, User
from progress.service import course_progress
from progress.stats import stats_for
from submissions import service as sub_svc
from submissions.models import Submission

learning = APIRouter(tags=["learning"])


async def _open_step(db: AsyncSession, user: User, step_id: int):
    """A visible step the user may open: 404 if hidden, 403 if still locked."""
    step, rev, module = await svc.get_step(db, step_id, for_student=True)
    await ensure_enrolled(db, user, module.course_id)
    await ensure_unlocked(db, user, step, module)
    return step, rev, module


async def _explanations(
    db: AsyncSession, user: User, subs: list[Submission]
) -> dict[int, dict | None]:
    """Answer-revealing feedback for submissions of steps whose answer the
    user may see now (show_answer), built against the revision they answered."""
    open_steps: dict[int, Step] = {}
    for step_id in {s.step_id for s in subs}:
        step = await db.get(Step, step_id)
        current = await db.get(StepRevision, step.current_revision_id)
        stats = (await stats_for(db, user.id, [step_id]))[step_id]
        if sub_svc.answer_available(svc.parse(step, current), stats):
            open_steps[step_id] = step
    result: dict[int, dict | None] = {}
    for s in subs:
        step = open_steps.get(s.step_id)
        if step is None:
            result[s.id] = None
            continue
        parsed = svc.parse(step, await db.get(StepRevision, s.step_revision_id))
        answer = parsed.type.answer_model.model_validate(s.answer)
        result[s.id] = parsed.type.explain(parsed.content, parsed.answer_key, answer)
    return result


async def _submissions_out(
    db: AsyncSession, user: User, subs: list[Submission]
) -> list[SubmissionOut]:
    due = await submission_deadlines(db, subs)
    explained = await _explanations(db, user, subs)
    return [
        SubmissionOut.model_validate(s).model_copy(
            update={
                "deadline_due_at": due[s.id],
                "is_late": is_late(s, due[s.id]),
                "explanation": explained[s.id],
            }
        )
        for s in subs
    ]


@learning.get("/courses", response_model=list[StudentCourseListItem])
@access_note("Только опубликованные курсы.")
async def list_courses(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(access_db)
):
    query = (
        select(Course)
        .where(Course.is_published, Course.deleted_at.is_(None))
        .order_by(Course.title)
    )
    if user.role == Role.STUDENT:
        query = query.where(Course.id.in_(enrolled_course_ids(user.id)))
    items = []
    for course in await db.scalars(query):
        progress = (await course_progress(db, course, [user]))[user.id]
        items.append(
            StudentCourseListItem(
                id=course.id,
                slug=course.slug,
                title=course.title,
                progress=progress.summary(),
            )
        )
    return items


@learning.get("/courses/{course_id}", response_model=StudentCourse)
@access_note(
    "Только опубликованный курс, скрытые шаги не показываются. В курсе с "
    "последовательным доступом закрытые для ученика шаги помечены `locked`; "
    "администраторы и кураторы видят все шаги открытыми."
)
async def get_course(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    course = await svc.get_course(db, course_id)
    if not course.is_published:
        raise svc.not_found("Course")
    await ensure_enrolled(db, user, course.id)
    modules = await svc.live_modules(db, course.id)
    rows = (
        await db.execute(
            select(Step, StepRevision.max_score)
            .join(StepRevision, StepRevision.id == Step.current_revision_id)
            .where(
                Step.module_id.in_([m.id for m in modules]),
                Step.deleted_at.is_(None),
                Step.is_hidden.is_(False),
            )
            .order_by(Step.position)
        )
    ).all()
    progress = (await course_progress(db, course, [user]))[user.id]
    locked = await locked_steps(db, user, course)
    group_id = await student_group_id(db, user)
    deadlines = await effective_deadlines(db, group_id, course.id)
    steps: dict[int, list[StudentStepSummary]] = {m.id: [] for m in modules}
    for step, max_score in rows:
        steps[step.module_id].append(
            StudentStepSummary(
                id=step.id,
                type=step.type,
                max_score=max_score,
                progress=progress.by_step[step.id].as_schema(),
                locked=step.id in locked,
                deadline=deadline_view(step.id, deadlines.get(step.id)),
            )
        )
    return StudentCourse(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        step_access=course.step_access,
        progress=progress.summary(),
        modules=[
            StudentModule(
                id=m.id,
                title=m.title,
                progress=progress.module_totals(m.id),
                steps=steps[m.id],
            )
            for m in modules
        ],
    )


@learning.get("/steps/{step_id}", response_model=StudentStep)
@access_note(
    "Только шаги опубликованного курса, кроме скрытых. В курсе с последовательным "
    "доступом ученику закрытый шаг недоступен (403); администраторы и кураторы "
    "видят все шаги."
)
async def get_step(
    step_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    step, rev, module = await _open_step(db, user, step_id)
    parsed = svc.parse(step, rev)
    stats = (await stats_for(db, user.id, [step.id]))[step.id]
    block = sub_svc.submit_block_reason(parsed, stats)
    course = await db.get(Course, module.course_id)
    progress = (await course_progress(db, course, [user]))[user.id]
    group_id = await student_group_id(db, user)
    deadlines = await effective_deadlines(db, group_id, module.course_id)
    return StudentStep(
        id=step.id,
        course_id=module.course_id,
        module_id=module.id,
        type=step.type,
        max_score=rev.max_score,
        # Only the content: the answer key never goes to students here.
        content=parsed.content.model_dump(mode="json"),
        grading=parsed.settings.grading,
        max_attempts=parsed.settings.max_attempts,
        show_answer=parsed.settings.show_answer,
        attempts_used=stats.attempts_used,
        progress=progress.by_step[step.id].as_schema(),
        answer_available=sub_svc.answer_available(parsed, stats),
        can_submit=block is None,
        submit_block_reason=block,
        deadline=deadline_view(step.id, deadlines.get(step.id)),
    )


@learning.get("/steps/{step_id}/answer")
@access_note(
    "Только шаги опубликованного курса, кроме скрытых. В курсе с последовательным "
    "доступом ученику закрытый шаг недоступен (403); администраторы и кураторы "
    "видят все шаги. Ответ отдаётся, только если это разрешает настройка задания "
    "`show_answer`."
)
async def get_answer(
    step_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
) -> dict:
    """The correct answer, when the step's show_answer policy allows it."""
    step, rev, _ = await _open_step(db, user, step_id)
    parsed = svc.parse(step, rev)
    stats = (await stats_for(db, user.id, [step.id]))[step.id]
    if not sub_svc.answer_available(parsed, stats):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The answer is not available")
    return parsed.type.reveal(parsed.answer_key)


@learning.post(
    "/steps/{step_id}/submissions", response_model=SubmissionOut, status_code=201
)
@access_note(
    "Только шаги опубликованного курса, кроме скрытых. В курсе с последовательным "
    "доступом ученику закрытый шаг недоступен (403); администраторы и кураторы "
    "видят все шаги. Новое решение можно отправить, пока предыдущее не на проверке, "
    "остались попытки и не набран максимальный балл."
)
async def submit(
    step_id: int,
    data: SubmitIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    step, rev, _ = await _open_step(db, user, step_id)
    sub = await sub_svc.submit(db, user, step, rev, data.answer)
    return (await _submissions_out(db, user, [sub]))[0]


@learning.get("/steps/{step_id}/submissions", response_model=list[SubmissionOut])
@access_note(
    "Только шаги опубликованного курса, кроме скрытых. В курсе с последовательным "
    "доступом ученику закрытый шаг недоступен (403); администраторы и кураторы "
    "видят все шаги. Только свои решения."
)
async def my_submissions(
    step_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    step, _, _ = await _open_step(db, user, step_id)
    query = (
        select(Submission)
        .where(Submission.user_id == user.id, Submission.step_id == step.id)
        .order_by(Submission.id.desc())
    )
    return await _submissions_out(db, user, list(await db.scalars(query)))


@learning.get("/submissions/{submission_id}", response_model=SubmissionOut)
@access_note("Только своё решение.")
async def my_submission(
    submission_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    sub = await db.get(Submission, submission_id)
    if not sub or sub.user_id != user.id:
        raise svc.not_found("Submission")
    return (await _submissions_out(db, user, [sub]))[0]
