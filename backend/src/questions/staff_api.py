"""Curator cabinet: questions of students, answers and who sees them."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import require_curator
from courses.models import Course, Module, Step
from courses.service import not_found, now
from database import access_db
from groups.service import students_of_curator
from models import Role, User
from questions import service
from questions.models import Question
from questions.schemas import QuestionUpdate, StaffQuestion

staff_questions = APIRouter(prefix="/questions", tags=["questions"])

SEE_RULE = (
    "Куратор видит вопросы учеников своих групп и вопросы, открытые всем; "
    "администратор — все."
)
ANSWER_RULE = (
    "Только куратор группы автора или администратор; вопрос чужой группы — 404, "
    "открытый всем вопрос чужой группы — 403."
)


async def _rows(db: AsyncSession, user: User, *conditions):
    query = (
        select(Question, User, Module, Course)
        .join(User, User.id == Question.author_id)
        .join(Step, Step.id == Question.step_id)
        .join(Module, Module.id == Step.module_id)
        .join(Course, Course.id == Module.course_id)
        .where(
            await service.visible_filter(db, user),
            Step.deleted_at.is_(None),
            Module.deleted_at.is_(None),
            Course.deleted_at.is_(None),
            *conditions,
        )
    )
    return query


async def _get_answerable(db: AsyncSession, user: User, question_id: int):
    query = await _rows(db, user, Question.id == question_id)
    row = (await db.execute(query.with_for_update(of=Question))).one_or_none()
    if row is None:
        # 404, not 403: do not reveal questions of other groups.
        raise not_found("Question")
    if not await service.can_answer(db, user, row[0]):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the curator of the author's group or an admin may answer",
        )
    return row


async def _answerable_authors(db: AsyncSession, user: User) -> set[int] | None:
    """Authors whose questions the user may answer; None means everyone."""
    if user.role == Role.ADMIN:
        return None
    return set(await db.scalars(students_of_curator(user.id)))


def _view(row, answerable: set[int] | None) -> StaffQuestion:
    question, author, module, course = row
    return StaffQuestion(
        id=question.id,
        step_id=question.step_id,
        course_id=course.id,
        course_title=course.title,
        module_title=module.title,
        author_id=author.id,
        author_username=author.username,
        author_name=author.name,
        author_surname=author.surname,
        author_patronymic=author.patronymic,
        text=question.text,
        created_at=question.created_at,
        answer=question.answer,
        answered_by=question.answered_by,
        answered_at=question.answered_at,
        visibility=question.visibility,
        group_id=question.group_id,
        can_answer=answerable is None or author.id in answerable,
        waiting_seconds=(
            int((now() - question.created_at).total_seconds())
            if question.answer is None
            else None
        ),
    )


@staff_questions.get("", response_model=list[StaffQuestion])
@access_note(SEE_RULE)
async def list_questions(
    answered: bool | None = None,
    course_id: int | None = None,
    step_id: int | None = None,
    student_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    """Вопросы учеников, от старых к новым (очередь). `answered=false` —
    только ждущие ответа."""
    conditions = []
    if answered is not None:
        conditions.append(
            Question.answer.is_not(None) if answered else Question.answer.is_(None)
        )
    if course_id is not None:
        conditions.append(Course.id == course_id)
    if step_id is not None:
        conditions.append(Question.step_id == step_id)
    if student_id is not None:
        conditions.append(Question.author_id == student_id)
    query = await _rows(db, user, *conditions)
    rows = (
        await db.execute(query.order_by(Question.id).limit(limit).offset(offset))
    ).all()
    answerable = await _answerable_authors(db, user)
    return [_view(row, answerable) for row in rows]


@staff_questions.patch("/{question_id}", response_model=StaffQuestion)
@access_note(ANSWER_RULE)
async def update_question(
    question_id: int,
    data: QuestionUpdate,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    """Ответить на вопрос (ответ можно исправить) и/или выбрать, кому он виден:
    `private` — автору, `group` — всей группе автора (на момент публикации),
    `course` — всем ученикам, которые проходят шаг. Открыть можно только
    вопрос с ответом. Автору при первом ответе приходит уведомление."""
    row = await _get_answerable(db, user, question_id)
    question = row[0]
    await service.update(
        db,
        user,
        question,
        data.model_fields_set,
        data.answer.strip() if data.answer else None,
        data.visibility,
    )
    await db.flush()
    return _view(row, await _answerable_authors(db, user))


@staff_questions.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
@access_note(ANSWER_RULE)
async def delete_question(
    question_id: int,
    user: User = Depends(require_curator),
    db: AsyncSession = Depends(access_db),
):
    """Удалить вопрос (например, не по теме)."""
    row = await _get_answerable(db, user, question_id)
    await db.delete(row[0])
