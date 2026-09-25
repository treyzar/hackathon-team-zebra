"""Submission pipeline shared by all step types:
validate answer -> check attempts -> grade (sync / queue for the judge / curator)."""

from dataclasses import dataclass

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from courses.models import Step, StepRevision
from courses.service import now, parse
from files.models import File, FilePurpose, FileStatus
from models import User
from steps.base import FileInfo, GradeResult, Grading, ShowAnswer
from steps.registry import ParsedRevision
from submissions.models import Submission, SubmissionStatus

from notifications.models import NotificationType, Severity as NotificationSeverity
from notifications.payloads import SubmissionReviewedPayload
from notifications.service import create_notification

def unprocessable(detail) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


@dataclass
class StepStats:
    """A student's standing on a step, from non-outdated submissions."""

    attempts_used: int = 0
    best_score: float | None = None
    solved: bool = False
    failed: bool = False
    in_progress: bool = False

    @property
    def state(self) -> str:
        if self.solved:
            return "solved"
        if self.in_progress:
            return "in_progress"
        if self.failed:
            return "failed"
        return "none"


async def stats_for(
    db: AsyncSession, user_id: int, step_ids: list[int]
) -> dict[int, StepStats]:
    rows = await db.execute(
        select(Submission.step_id, Submission.status, Submission.score).where(
            Submission.user_id == user_id,
            Submission.step_id.in_(step_ids),
            Submission.is_outdated.is_(False),
        )
    )
    result = {step_id: StepStats() for step_id in step_ids}
    for step_id, st, score in rows:
        s = result[step_id]
        if st != SubmissionStatus.ERROR:  # judge failures are not attempts
            s.attempts_used += 1
        if score is not None and (s.best_score is None or score > s.best_score):
            s.best_score = score
        s.solved |= st.solved
        s.failed |= st.failed
        s.in_progress |= st.in_progress
    return result


def answer_available(parsed: ParsedRevision, stats: StepStats) -> bool:
    s = parsed.settings
    match s.show_answer:
        case ShowAnswer.AFTER_WRONG:
            return stats.failed
        case ShowAnswer.AFTER_ATTEMPTS_EXHAUSTED:
            return s.max_attempts is not None and stats.attempts_used >= s.max_attempts
        case ShowAnswer.AFTER_SOLVED:
            return stats.solved
    return False


def submit_block_reason(parsed: ParsedRevision, stats: StepStats) -> str | None:
    """Why the student may not submit again, or None if they may: a new try
    is allowed while attempts remain and the maximum score is not reached."""
    if stats.in_progress:
        return "The previous submission is still being checked"
    if stats.best_score is not None and stats.best_score >= parsed.max_score:
        return "The step is already solved with the maximum score"
    max_attempts = parsed.settings.max_attempts
    if max_attempts is not None and stats.attempts_used >= max_attempts:
        return "No attempts left"
    return None


def status_for_score(score: float, max_score: int) -> SubmissionStatus:
    if score >= max_score:
        return SubmissionStatus.CORRECT
    return SubmissionStatus.PARTIAL if score > 0 else SubmissionStatus.WRONG


def apply_auto_result(
    sub: Submission, grading: Grading, result: GradeResult, max_score: int
) -> None:
    sub.auto_score = result.score
    sub.result_details = result.details
    if grading.uses_review:
        sub.status = SubmissionStatus.PENDING_REVIEW
    else:
        sub.score = result.score
        sub.status = status_for_score(result.score, max_score)


async def _check_files(
    db: AsyncSession, user: User, parsed: ParsedRevision, answer
) -> None:
    ids = parsed.type.answer_files(answer)
    if not ids:
        parsed.type.check_files(parsed.content, [])
        return
    if len(set(ids)) != len(ids):
        raise unprocessable("Duplicate file")
    found = (
        await db.scalars(
            select(File).where(
                File.id.in_(ids),
                File.owner_id == user.id,
                File.purpose == FilePurpose.SUBMISSION,
                File.status == FileStatus.READY,
            )
        )
    ).all()
    if len(found) != len(ids):
        raise unprocessable("Unknown or not uploaded file")
    try:
        parsed.type.check_files(
            parsed.content, [FileInfo(id=f.id, mime=f.mime, size=f.size) for f in found]
        )
    except ValueError as e:
        raise unprocessable(str(e)) from e


async def submit(
    db: AsyncSession, user: User, step: Step, rev: StepRevision, raw_answer: dict
) -> Submission:
    parsed = parse(step, rev)
    t = parsed.type
    try:
        answer = t.answer_model.model_validate(raw_answer)
        t.validate_answer(parsed.content, answer)
    except ValidationError as e:
        raise unprocessable(jsonable_encoder(e.errors(include_url=False))) from e
    except ValueError as e:
        raise unprocessable(str(e)) from e
    await _check_files(db, user, parsed, answer)

    # Serialize concurrent submits of the same student to the same step,
    # otherwise both could pass the attempts check.
    await db.execute(select(func.pg_advisory_xact_lock(user.id, step.id)))
    stats = (await stats_for(db, user.id, [step.id]))[step.id]
    if reason := submit_block_reason(parsed, stats):
        raise HTTPException(status.HTTP_409_CONFLICT, reason)

    sub = Submission(
        user_id=user.id,
        step_id=step.id,
        step_revision_id=rev.id,
        answer=answer.model_dump(mode="json"),
        result_details={},
        is_outdated=False,
        judge_attempts=0,
    )
    grading = parsed.settings.grading
    if grading in (Grading.NONE, Grading.AUTO):
        result = t.check(
            parsed.content, parsed.answer_key, parsed.settings, answer, parsed.max_score
        )
        apply_auto_result(sub, grading, result, parsed.max_score)
    elif grading.uses_tests:
        sub.status = SubmissionStatus.QUEUED
    else:
        sub.status = SubmissionStatus.PENDING_REVIEW
    db.add(sub)
    await db.flush()
    return sub


async def apply_review(
    db: AsyncSession,
    sub: Submission,
    reviewer: User,
    accepted: bool,
    score: float | None,
    comment: str | None,
    max_score: int,
) -> None:
    if sub.status != SubmissionStatus.PENDING_REVIEW:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Submission is not awaiting review"
        )
    if score is None:
        # Accepted: keep the tests' score if there were tests, else full score.
        score = (
            (sub.auto_score if sub.auto_score is not None else max_score)
            if accepted
            else 0
        )
    if not 0 <= score <= max_score:
        raise unprocessable(f"Score must be between 0 and {max_score}")
    sub.status = SubmissionStatus.ACCEPTED if accepted else SubmissionStatus.REJECTED
    sub.score = score
    sub.reviewer_id = reviewer.id
    sub.reviewed_at = now()
    sub.review_comment = comment

    course_id = await db.scalar(
        select(Module.course_id).
        join(Step,Step.module_id==Module.id).
        where(Step.id == sub.step_id)
    )
    await create_notification(
        db,
        sub.user_id,
        NotificationType.SUBMISSION_REVIEWED,
        SubmissionReviewedPayload(
            submission_id=sub.id,
            step_id=sub.step_id,
            course_id=course_id,
            verdict=sub.status.value,
            score=score,
            max_score=max_score,
        ),
        severity=(
            NotificationSeverity.SUCCESS if accepted else NotificationSeverity.WARNING
        ),
        dedup_key=f"{NotificationType.SUBMISSION_REVIEWED}:{sub.id}",
    )