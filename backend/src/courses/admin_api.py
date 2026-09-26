import json

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import require_admin
from courses import service as svc
from courses.export_import import export_as_archive, export_as_json
from courses.export_import import import_course as import_from_json
from courses.models import Course, Enrollment, Module, Step, StepRevision
from courses.pdf_export import export_as_pdf
from courses.schemas import (
    AdminCourseTree,
    AdminModuleOut,
    AdminStepOut,
    AdminStepSummary,
    CourseCreate,
    CourseOut,
    CourseUpdate,
    EnrolledStudent,
    EnrollIn,
    EnrollResult,
    ImportResult,
    ModuleIn,
    ModuleUpdate,
    Order,
    RevisionOut,
    RevisionSummary,
    StepFlags,
    StepSave,
)
from database import access_db
from groups.models import Group, GroupStudent
from models import Role, User

authoring = APIRouter(
    prefix="/admin", tags=["authoring"], dependencies=[Depends(require_admin)]
)


async def _flush_slug(db: AsyncSession) -> None:
    try:
        await db.flush()
    except IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug is taken") from e


# --- courses ---------------------------------------------------------------


@authoring.get("/courses", response_model=list[CourseOut])
async def list_courses(db: AsyncSession = Depends(access_db)):
    query = select(Course).where(Course.deleted_at.is_(None)).order_by(Course.id)
    return (await db.scalars(query)).all()


@authoring.post("/courses", response_model=CourseOut, status_code=201)
async def create_course(data: CourseCreate, db: AsyncSession = Depends(access_db)):
    course = Course(
        slug=data.slug,
        title=data.title,
        description=data.description.model_dump(mode="json"),
        is_published=False,
        step_access=data.step_access,
    )
    db.add(course)
    await _flush_slug(db)
    return course


@authoring.get("/courses/{course_id}", response_model=AdminCourseTree)
async def get_course_tree(course_id: int, db: AsyncSession = Depends(access_db)):
    course = await svc.get_course(db, course_id)
    modules = await svc.live_modules(db, course.id)
    rows = await db.execute(
        select(Step, StepRevision.max_score, StepRevision.number)
        .join(StepRevision, StepRevision.id == Step.current_revision_id)
        .where(Step.module_id.in_([m.id for m in modules]), Step.deleted_at.is_(None))
        .order_by(Step.position)
    )
    steps: dict[int, list[AdminStepSummary]] = {m.id: [] for m in modules}
    for step, max_score, number in rows:
        steps[step.module_id].append(
            AdminStepSummary(
                id=step.id,
                type=step.type,
                position=step.position,
                is_hidden=step.is_hidden,
                max_score=max_score,
                revision_number=number,
            )
        )
    return AdminCourseTree(
        **CourseOut.model_validate(course).model_dump(),
        modules=[
            AdminModuleOut(
                id=m.id,
                title=m.title,
                position=m.position,
                skills=m.skills,
                steps=steps[m.id],
            )
            for m in modules
        ],
    )


@authoring.patch("/courses/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int, data: CourseUpdate, db: AsyncSession = Depends(access_db)
):
    course = await svc.get_course(db, course_id)
    for field in ("slug", "title", "is_published", "step_access"):
        value = getattr(data, field)
        if value is not None:
            setattr(course, field, value)
    if data.description is not None:
        course.description = data.description.model_dump(mode="json")
    await _flush_slug(db)
    return course


@authoring.delete("/courses/{course_id}", status_code=204)
async def delete_course(course_id: int, db: AsyncSession = Depends(access_db)):
    svc.soft_delete(await svc.get_course(db, course_id))


# --- modules ---------------------------------------------------------------


@authoring.post(
    "/courses/{course_id}/modules", response_model=AdminModuleOut, status_code=201
)
async def create_module(
    course_id: int, data: ModuleIn, db: AsyncSession = Depends(access_db)
):
    course = await svc.get_course(db, course_id)
    position = await svc.next_position(db, Module.position, Module.course_id, course.id)
    module = Module(
        course_id=course.id, title=data.title, position=position, skills=data.skills
    )
    db.add(module)
    await db.flush()
    return AdminModuleOut(
        id=module.id,
        title=module.title,
        position=position,
        skills=module.skills,
        steps=[],
    )


@authoring.put("/courses/{course_id}/modules/order", status_code=204)
async def reorder_modules(
    course_id: int, data: Order, db: AsyncSession = Depends(access_db)
):
    course = await svc.get_course(db, course_id)
    modules = await db.scalars(
        select(Module).where(Module.course_id == course.id, Module.deleted_at.is_(None))
    )
    await svc.reorder(db, list(modules), data.ids)


@authoring.patch("/modules/{module_id}", status_code=204)
async def update_module(
    module_id: int, data: ModuleUpdate, db: AsyncSession = Depends(access_db)
):
    """Переименовать модуль и/или задать его навыки для карты навыков."""
    module = await svc.get_module(db, module_id)
    if data.title is not None:
        module.title = data.title
    if data.skills is not None:
        module.skills = data.skills


@authoring.delete("/modules/{module_id}", status_code=204)
async def delete_module(module_id: int, db: AsyncSession = Depends(access_db)):
    svc.soft_delete(await svc.get_module(db, module_id))


@authoring.put("/modules/{module_id}/steps/order", status_code=204)
async def reorder_steps(
    module_id: int, data: Order, db: AsyncSession = Depends(access_db)
):
    module = await svc.get_module(db, module_id)
    steps = await db.scalars(
        select(Step).where(Step.module_id == module.id, Step.deleted_at.is_(None))
    )
    await svc.reorder(db, list(steps), data.ids)


# --- steps -----------------------------------------------------------------


def _step_out(step: Step, rev: StepRevision) -> AdminStepOut:
    return AdminStepOut(
        id=step.id,
        module_id=step.module_id,
        type=step.type,
        position=step.position,
        is_hidden=step.is_hidden,
        revision=RevisionOut.model_validate(rev),
    )


@authoring.post(
    "/modules/{module_id}/steps", response_model=AdminStepOut, status_code=201
)
async def create_step(
    module_id: int,
    data: StepSave,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(access_db),
):
    module = await svc.get_module(db, module_id)
    position = await svc.next_position(db, Step.position, Step.module_id, module.id)
    step = Step(
        module_id=module.id,
        type=data.payload.type,
        position=position,
        is_hidden=False,
    )
    db.add(step)
    await db.flush()
    rev = await svc.add_revision(db, step, data.payload, user, data.comment, False)
    return _step_out(step, rev)


@authoring.get("/steps/{step_id}", response_model=AdminStepOut)
async def get_step(step_id: int, db: AsyncSession = Depends(access_db)):
    step, rev, _ = await svc.get_step(db, step_id)
    return _step_out(step, rev)


@authoring.post("/steps/{step_id}/revisions", response_model=AdminStepOut)
async def save_step(
    step_id: int,
    data: StepSave,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(access_db),
):
    """Save a new revision of the step; history is kept."""
    step, current, _ = await svc.get_step(db, step_id)
    if data.payload.type != step.type:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Step type cannot be changed"
        )
    if data.base_revision is not None and data.base_revision != current.number:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Step was changed (now revision {current.number}), reload it",
        )
    rev = await svc.add_revision(
        db, step, data.payload, user, data.comment, data.is_breaking
    )
    return _step_out(step, rev)


@authoring.get("/steps/{step_id}/revisions", response_model=list[RevisionSummary])
async def list_revisions(step_id: int, db: AsyncSession = Depends(access_db)):
    step, _, _ = await svc.get_step(db, step_id)
    query = (
        select(StepRevision)
        .where(StepRevision.step_id == step.id)
        .order_by(StepRevision.number.desc())
    )
    return (await db.scalars(query)).all()


@authoring.get("/steps/{step_id}/revisions/{number}", response_model=RevisionOut)
async def get_revision(
    step_id: int, number: int, db: AsyncSession = Depends(access_db)
):
    step, _, _ = await svc.get_step(db, step_id)
    rev = await db.scalar(
        select(StepRevision).where(
            StepRevision.step_id == step.id, StepRevision.number == number
        )
    )
    if not rev:
        raise svc.not_found("Revision")
    return rev


@authoring.patch("/steps/{step_id}", status_code=204)
async def set_step_flags(
    step_id: int, data: StepFlags, db: AsyncSession = Depends(access_db)
):
    step, _, _ = await svc.get_step(db, step_id)
    step.is_hidden = data.is_hidden


@authoring.delete("/steps/{step_id}", status_code=204)
async def delete_step(step_id: int, db: AsyncSession = Depends(access_db)):
    step, _, _ = await svc.get_step(db, step_id)
    svc.soft_delete(step)


# --- enrollment --------------------------------------------------------------


@authoring.post("/courses/{course_id}/enrollments", response_model=EnrollResult)
@access_note(
    "Записывает на курс учеников из `user_ids` и текущих учеников групп из "
    "`group_ids` (снимок: кто придёт в группу позже, записывается отдельно). "
    "Ученик видит только курсы, на которые записан. Можно передать только "
    "учеников; повторная запись ничего не меняет."
)
async def enroll(
    course_id: int,
    data: EnrollIn,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(access_db),
):
    course = await svc.get_course(db, course_id)
    ids = set(data.user_ids)
    if data.group_ids:
        found = set(
            await db.scalars(select(Group.id).where(Group.id.in_(data.group_ids)))
        )
        if missing := set(data.group_ids) - found:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Unknown groups: {sorted(missing)}",
            )
        ids |= set(
            await db.scalars(
                select(GroupStudent.user_id).where(
                    GroupStudent.group_id.in_(data.group_ids)
                )
            )
        )
    if data.user_ids:
        students = set(
            await db.scalars(
                select(User.id).where(
                    User.id.in_(data.user_ids), User.role == Role.STUDENT
                )
            )
        )
        if bad := set(data.user_ids) - students:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Not students or unknown users: {sorted(bad)}",
            )
    already = set(
        await db.scalars(
            select(Enrollment.user_id).where(
                Enrollment.course_id == course.id, Enrollment.user_id.in_(ids)
            )
        )
    )
    new = sorted(ids - already)
    db.add_all(
        Enrollment(course_id=course.id, user_id=uid, enrolled_by=user.id) for uid in new
    )
    return EnrollResult(enrolled=new, already_enrolled=sorted(already))


@authoring.get("/courses/{course_id}/enrollments", response_model=list[EnrolledStudent])
async def list_enrollments(course_id: int, db: AsyncSession = Depends(access_db)):
    course = await svc.get_course(db, course_id)
    rows = await db.execute(
        select(User.id, User.username, GroupStudent.group_id)
        .join(Enrollment, Enrollment.user_id == User.id)
        .outerjoin(GroupStudent, GroupStudent.user_id == User.id)
        .where(Enrollment.course_id == course.id)
        .order_by(User.username)
    )
    return [EnrolledStudent(id=i, username=n, group_id=g) for i, n, g in rows]


@authoring.delete("/courses/{course_id}/enrollments/{user_id}", status_code=204)
@access_note(
    "Ученик теряет доступ к курсу; его решения и результаты сохраняются и "
    "вернутся при повторной записи."
)
async def unenroll(course_id: int, user_id: int, db: AsyncSession = Depends(access_db)):
    enrollment = await db.get(Enrollment, (course_id, user_id))
    if enrollment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not enrolled")
    await db.delete(enrollment)


@authoring.get("/courses/{course_id}/export")
async def export_course_json(
    course_id: int, db: AsyncSession = Depends(access_db)
) -> Response:
    course = await svc.get_course(db, course_id)
    document = await export_as_json(db, course)
    payload = await export_as_archive(db, course, document)
    if payload is None:
        body = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{course.slug}.json"'
            },
        )
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{course.slug}.zip"'},
    )


@authoring.get("/courses/{course_id}/export_pdf")
async def export_course_pdf(
    course_id: int, db: AsyncSession = Depends(access_db)
) -> Response:
    course = await svc.get_course(db, course_id)
    pdf = await export_as_pdf(db, course, include_answers=True)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{course.slug}.pdf"'},
    )


@authoring.post("/courses/import", response_model=ImportResult, status_code=201)
async def import_course(
    file: UploadFile,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(access_db),
) -> ImportResult:
    raw = await file.read()
    course, warnings = await import_from_json(db, user, raw)
    return ImportResult(
        course_id=course.id,
        slug=course.slug,
        title=course.title,
        warnings=warnings,
    )


# @authoring.post("/courses/import", response_model=CourseOut, status_code=201)
# async def import_course(
#    file: UploadFile,
#    user: User = Depends(require_admin),
#    db: AsyncSession = Depends(access_db),
# ) -> CourseOut:
#    raw = await file.read()
#    course, _warnings = await import_course(db, user, raw)
#    return course
