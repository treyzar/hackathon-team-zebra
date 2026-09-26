"""A student's skill map: every course they study with the skills of its
modules.

A module's skills (set by an admin) are earned together, by the module:

- gold: every visible step of the module is completed (by the same rule as
  course progress), and every task of it (a step with points) reached its
  maximum on the first attempt;
- done (green): every visible step is completed;
- in_progress: some work on the module was sent, not all of it is completed;
- locked: the course opens steps one by one and none of the module's steps
  is open yet — it opens after the previous module;
- open: can be started.

A module without visible steps earns nothing and stays open. Computed on
request from progress and submissions, like everything in this package:
editing a course or grading work changes the map at once.
"""

import enum

from sqlalchemy.ext.asyncio import AsyncSession

from courses.access import locked_steps
from courses.service import live_modules
from models import User
from progress.analytics import StepWork, step_work
from progress.schemas import CourseSkills, Skill
from progress.service import StepResult, StepState, course_progress, studied_courses


class SkillState(enum.StrEnum):
    LOCKED = "locked"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    GOLD = "gold"


def module_state(
    results: list[StepResult], work: dict[int, StepWork], locked: set[int]
) -> SkillState:
    """State of a module's skills from its steps' results; ``work`` is the
    student's attempts by step id, ``locked`` the steps not open yet."""
    if results and all(r.completed for r in results):
        first_try = all(
            work.get(r.step.id, StepWork()).first_solved
            for r in results
            if r.step.max_score > 0
        )
        return SkillState.GOLD if first_try else SkillState.DONE
    if any(r.step.id in work or r.completed for r in results):
        return SkillState.IN_PROGRESS
    if results and all(r.step.id in locked for r in results):
        return SkillState.LOCKED
    return SkillState.OPEN


async def skill_map(db: AsyncSession, user: User) -> list[CourseSkills]:
    result = []
    for course in (await studied_courses(db, [user.id]))[user.id]:
        progress = (await course_progress(db, course, [user]))[user.id]
        locked = await locked_steps(db, user, course)
        work = {
            step_id: w
            for (_, step_id), w in (
                await step_work(db, [user], [r.step.id for r in progress.steps])
            ).items()
        }
        skills, previous = [], None
        for module in await live_modules(db, course.id):
            steps = [r for r in progress.steps if r.step.module_id == module.id]
            state = module_state(steps, work, locked)
            # Returned work waiting for a new attempt; a completed step is
            # not "returned" any more.
            returned = sum(
                work.get(r.step.id, StepWork()).unresolved_return and not r.completed
                for r in steps
            )
            checking = sum(r.state == StepState.CHECKING for r in steps)
            completed = sum(r.completed for r in steps)
            next_step = next(
                (
                    r.step.id
                    for r in steps
                    if not r.completed
                    and r.state != StepState.CHECKING
                    and r.step.id not in locked
                ),
                None,
            )
            skills += [
                Skill(
                    name=name,
                    module_id=module.id,
                    module_title=module.title,
                    state=state,
                    steps_total=len(steps),
                    steps_completed=completed,
                    steps_checking=checking,
                    steps_returned=returned,
                    next_step_id=next_step,
                    current=progress.next_step_id is not None
                    and any(r.step.id == progress.next_step_id for r in steps),
                    opens_after=(
                        previous.title
                        if state == SkillState.LOCKED and previous
                        else None
                    ),
                )
                for name in module.skills
            ]
            if steps:
                previous = module
        result.append(
            CourseSkills(course_id=course.id, title=course.title, skills=skills)
        )
    return result
