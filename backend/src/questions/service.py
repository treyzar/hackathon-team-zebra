"""Questions about steps: who sees them, who answers, notifications.

A question is always visible to its author, to the curator of the author's
group and to admins. The answer does not change that; a curator may then
open the question with its answer to the author's group or to everyone who
studies the step. Other students never learn who asked.
"""

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, and_, false, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from courses.models import Module, Step
from courses.service import now
from groups.models import Group
from groups.service import can_see_student, student_group_id, students_of_curator
from models import Role, User
from notifications.models import NotificationType
from notifications.payloads import QuestionAnsweredPayload, QuestionAskedPayload
from notifications.service import create_notification
from questions.models import Question, QuestionVisibility


async def visible_filter(db: AsyncSession, user: User) -> ColumnElement[bool]:
    """Condition on ``Question`` rows the user may read."""
    if user.role == Role.ADMIN:
        return true()
    public = Question.visibility == QuestionVisibility.COURSE
    if user.role == Role.CURATOR:
        # Like submissions: their own students' questions, plus public ones.
        return or_(Question.author_id.in_(students_of_curator(user.id)), public)
    group_id = await student_group_id(db, user)
    in_group = (
        and_(
            Question.visibility == QuestionVisibility.GROUP,
            Question.group_id == group_id,
        )
        if group_id is not None
        else false()
    )
    return or_(Question.author_id == user.id, in_group, public)


async def can_answer(db: AsyncSession, user: User, question: Question) -> bool:
    """Only who sees the author's work answers: the curator of the author's
    group and admins. A curator reading a public question of another group
    may not change it."""
    return user.role != Role.STUDENT and await can_see_student(
        db, user, question.author_id
    )


async def ask(
    db: AsyncSession, author: User, step: Step, module: Module, text: str
) -> Question:
    question = Question(step_id=step.id, author_id=author.id, text=text)
    db.add(question)
    await db.flush()
    group_id = await student_group_id(db, author)
    curator_id = (
        await db.scalar(select(Group.curator_id).where(Group.id == group_id))
        if group_id is not None
        else None
    )
    if curator_id is not None:
        await create_notification(
            db,
            curator_id,
            NotificationType.QUESTION_ASKED,
            QuestionAskedPayload(
                question_id=question.id,
                step_id=step.id,
                course_id=module.course_id,
                student_id=author.id,
            ),
        )
    return question


async def update(
    db: AsyncSession,
    staff: User,
    question: Question,
    fields: set[str],
    answer: str | None,
    visibility: QuestionVisibility | None,
) -> None:
    """Answer and/or change who sees the question."""
    first_answer = "answer" in fields and question.answer is None
    if "answer" in fields:
        question.answer = answer
        question.answered_by = staff.id
        question.answered_at = now()
    if visibility is not None and visibility != question.visibility:
        await _set_visibility(db, question, visibility)
    if question.visibility != QuestionVisibility.PRIVATE and question.answer is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Answer the question before making it public",
        )
    if first_answer:
        course_id = await db.scalar(
            select(Module.course_id)
            .join(Step, Step.module_id == Module.id)
            .where(Step.id == question.step_id)
        )
        await create_notification(
            db,
            question.author_id,
            NotificationType.QUESTION_ANSWERED,
            QuestionAnsweredPayload(
                question_id=question.id,
                step_id=question.step_id,
                course_id=course_id,
            ),
            dedup_key=f"{NotificationType.QUESTION_ANSWERED}:{question.id}",
        )


async def _set_visibility(
    db: AsyncSession, question: Question, visibility: QuestionVisibility
) -> None:
    question.visibility = visibility
    question.group_id = None
    if visibility == QuestionVisibility.GROUP:
        author = await db.get(User, question.author_id)
        question.group_id = await student_group_id(db, author)
        if question.group_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "The author is not in a group",
            )
