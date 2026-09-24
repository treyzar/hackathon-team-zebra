from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from courses import service as svc
from courses.models import Course, Module, Step, StepRevision
from courses.schemas import (
    CourseListItem,
    StepProgress,
    StudentCourse,
    StudentModule,
    StudentStep,
    StudentStepSummary,
    SubmissionOut,
    SubmitIn,
)
from database import access_db
from models import User
from submissions import service as sub_svc
from submissions.models import Submission

learning = APIRouter(tags=["learning"])


def _progress(stats: sub_svc.StepStats) -> StepProgress:
    return StepProgress(state=stats.state, best_score=stats.best_score)


@learning.get("/courses", response_model=list[CourseListItem])
async def list_courses(
    _: User = Depends(get_current_user), db: AsyncSession = Depends(access_db)
):
    query = (
        select(Course)
        .where(Course.is_published, Course.deleted_at.is_(None))
        .order_by(Course.title)
    )
    return (await db.scalars(query)).all()


@learning.get("/courses/{course_id}", response_model=StudentCourse)
async def get_course(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    course = await svc.get_course(db, course_id)
    if not course.is_published:
        raise svc.not_found("Course")
    modules = (
        await db.scalars(
            select(Module)
            .where(Module.course_id == course.id, Module.deleted_at.is_(None))
            .order_by(Module.position)
        )
    ).all()
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
    stats = await sub_svc.stats_for(db, user.id, [step.id for step, _ in rows])
    steps: dict[int, list[StudentStepSummary]] = {m.id: [] for m in modules}
    for step, max_score in rows:
        steps[step.module_id].append(
            StudentStepSummary(
                id=step.id,
                type=step.type,
                max_score=max_score,
                progress=_progress(stats[step.id]),
            )
        )
    return StudentCourse(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        modules=[
            StudentModule(id=m.id, title=m.title, steps=steps[m.id]) for m in modules
        ],
    )


@learning.get("/steps/{step_id}", response_model=StudentStep)
async def get_step(
    step_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    step, rev, module = await svc.get_step(db, step_id, for_student=True)
    parsed = svc.parse(step, rev)
    stats = (await sub_svc.stats_for(db, user.id, [step.id]))[step.id]
    block = sub_svc.submit_block_reason(parsed, stats)
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
        progress=_progress(stats),
        answer_available=sub_svc.answer_available(parsed, stats),
        can_submit=block is None,
        submit_block_reason=block,
    )


@learning.get("/steps/{step_id}/answer")
async def get_answer(
    step_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
) -> dict:
    """The correct answer, when the step's show_answer policy allows it."""
    step, rev, _ = await svc.get_step(db, step_id, for_student=True)
    parsed = svc.parse(step, rev)
    stats = (await sub_svc.stats_for(db, user.id, [step.id]))[step.id]
    if not sub_svc.answer_available(parsed, stats):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The answer is not available")
    return parsed.type.reveal(parsed.answer_key)


@learning.post(
    "/steps/{step_id}/submissions", response_model=SubmissionOut, status_code=201
)
async def submit(
    step_id: int,
    data: SubmitIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    step, rev, _ = await svc.get_step(db, step_id, for_student=True)
    return await sub_svc.submit(db, user, step, rev, data.answer)


@learning.get("/steps/{step_id}/submissions", response_model=list[SubmissionOut])
async def my_submissions(
    step_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    step, _, _ = await svc.get_step(db, step_id, for_student=True)
    query = (
        select(Submission)
        .where(Submission.user_id == user.id, Submission.step_id == step.id)
        .order_by(Submission.id.desc())
    )
    return (await db.scalars(query)).all()


@learning.get("/submissions/{submission_id}", response_model=SubmissionOut)
async def my_submission(
    submission_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(access_db),
):
    sub = await db.get(Submission, submission_id)
    if not sub or sub.user_id != user.id:
        raise svc.not_found("Submission")
    return sub
