"""A student's standing on the current version of a step.

This drives what the student may do now: attempts left, whether a new
submission is allowed, whether the answer may be shown. Submissions made
before a breaking change of the step (``is_outdated``) are left out, so the
student starts the new version with fresh attempts. Course progress, which
keeps those earlier results, is computed in progress/service.py.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from submissions.models import Submission, SubmissionStatus


@dataclass
class StepStats:
    attempts_used: int = 0
    best_score: float | None = None
    solved: bool = False
    failed: bool = False
    in_progress: bool = False


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
