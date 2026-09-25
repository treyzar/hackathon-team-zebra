"""Rating of students within their group for a course.

Formula: the rating is the sum of points earned in the course, exactly
``points_earned`` of progress (best attempt per step, a curator's grade counts
like an automatic one). Progress tells how far a student is through the
course; the rating tells where they stand among their group.

Places: place = 1 + number of groupmates with strictly more points, so equal
points share a place (6, 4, 4, 0 -> places 1, 2, 2, 4).

A student sees only their own data plus anonymous targets: the nearest higher
result (equal ones are skipped) and the first place, how many points are
needed to overtake them (strictly more than the gap), and which steps can
bring those points: steps to complete first, in course order, then steps with
partial points to improve.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from courses.models import Course
from models import User
from progress.schemas import MyRating, Opportunity, RankTarget, RatingRow
from progress.service import CourseProgress, StepState, course_progress, step_labels

_COMPLETE = (StepState.NOT_STARTED, StepState.FAILED)


@dataclass
class GroupRating:
    students: list[User]
    progress: dict[int, CourseProgress]

    def points(self, user_id: int) -> float:
        return self.progress[user_id].summary().points_earned

    def place(self, points: float) -> int:
        return 1 + sum(self.points(s.id) > points for s in self.students)

    def rows(self) -> list[RatingRow]:
        rows = [
            RatingRow(
                place=self.place(self.points(s.id)),
                student_id=s.id,
                username=s.username,
                points=self.points(s.id),
                steps_completed=self.progress[s.id].summary().steps_completed,
            )
            for s in self.students
        ]
        return sorted(rows, key=lambda r: (r.place, r.username))


async def group_rating(
    db: AsyncSession, course: Course, students: list[User]
) -> GroupRating:
    return GroupRating(students, await course_progress(db, course, students))


async def opportunities(
    db: AsyncSession, course: Course, progress: CourseProgress
) -> list[Opportunity]:
    """Where points can still be earned, in the order to go for them."""
    labels = await step_labels(db, course.id, [r.step for r in progress.steps])

    def opportunity(r, action: str) -> Opportunity:
        return Opportunity(
            step_id=r.step.id,
            module_id=r.step.module_id,
            module_title=labels[r.step.id].module_title,
            position=labels[r.step.id].position,
            type=r.step.type,
            action=action,
            can_gain=round(r.step.max_score - r.earned, 2),
        )

    # Steps without points count (theory) raise no rating: left out.
    open_ = [r for r in progress.steps if r.step.max_score > 0 and r.attempts_left]
    to_complete = [opportunity(r, "complete") for r in open_ if r.state in _COMPLETE]
    to_improve = [
        opportunity(r, "improve") for r in open_ if r.state == StepState.PARTIAL
    ]
    return to_complete + to_improve


def _target(
    place: int, points: float, mine: float, opps: list[Opportunity]
) -> RankTarget:
    if points <= mine:  # already there
        return RankTarget(place=place, points=points, gap=None, plan=[], reachable=True)
    gap = round(points - mine, 2)
    plan, gained = [], 0.0
    for o in opps:
        if round(gained, 2) > gap:
            break
        plan.append(o.step_id)
        gained += o.can_gain
    reachable = round(gained, 2) > gap
    return RankTarget(
        place=place,
        points=points,
        gap=gap,
        plan=plan if reachable else [],
        reachable=reachable,
    )


async def my_rating(
    db: AsyncSession, course: Course, user: User, rating: GroupRating
) -> MyRating:
    mine = rating.points(user.id)
    others = [rating.points(s.id) for s in rating.students if s.id != user.id]
    opps = await opportunities(db, course, rating.progress[user.id])

    higher = [p for p in others if p > mine]
    next_place = None
    if higher:
        nearest = min(higher)
        next_place = _target(rating.place(nearest), nearest, mine, opps)
    top = max([mine, *others])
    return MyRating(
        course_id=course.id,
        group_size=len(rating.students),
        points=mine,
        place=rating.place(mine),
        tied_with=sum(p == mine for p in others),
        next_place=next_place,
        first_place=_target(1, top, mine, opps),
        opportunities=opps,
    )
