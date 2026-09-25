"""Student cabinet: questions about a step."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_docs import access_note
from auth import require_roles
from courses.access import open_step
from database import access_db
from models import Role, User
from questions import service
from questions.models import Question
from questions.schemas import QuestionIn, StudentQuestion

student_questions = APIRouter(tags=["questions"])
require_student = require_roles(Role.STUDENT)

STEP_RULE = (
    "Только по шагу, который ученик может открыть: курс, на который он записан, "
    "и шаг не закрыт последовательным доступом."
)


def _view(question: Question, user: User) -> StudentQuestion:
    return StudentQuestion(
        id=question.id,
        step_id=question.step_id,
        text=question.text,
        created_at=question.created_at,
        is_mine=question.author_id == user.id,
        visibility=question.visibility,
        answer=question.answer,
        answered_at=question.answered_at,
    )


@student_questions.post(
    "/steps/{step_id}/questions",
    response_model=StudentQuestion,
    status_code=status.HTTP_201_CREATED,
)
@access_note(STEP_RULE)
async def ask_question(
    step_id: int,
    data: QuestionIn,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(access_db),
):
    """Задать вопрос по шагу. Его видят ученик, куратор его группы (ему
    приходит уведомление) и администраторы."""
    step, _, module = await open_step(db, user, step_id)
    question = await service.ask(db, user, step, module, data.text.strip())
    return _view(question, user)


@student_questions.get(
    "/steps/{step_id}/questions", response_model=list[StudentQuestion]
)
@access_note(
    STEP_RULE + " Видны свои вопросы и вопросы, которые куратор открыл группе "
    "ученика или всем; автор чужого вопроса не показывается."
)
async def list_step_questions(
    step_id: int,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(access_db),
):
    """Свои вопросы по шагу и открытые для ученика, от новых к старым."""
    await open_step(db, user, step_id)
    rows = await db.scalars(
        select(Question)
        .where(Question.step_id == step_id, await service.visible_filter(db, user))
        .order_by(Question.id.desc())
    )
    return [_view(q, user) for q in rows]
