"""Overall rating of a student within their group.

Formula: rating = points of every course the student studies (published
courses they are enrolled in; exactly ``points_earned`` of each course's
progress) + a streak bonus of 2 points per day of the current streak.

Streak: consecutive days (in ``settings.timezone``) with at least one
submission that earned points or is still waiting for a check (queued,
tested or with a curator). It runs up to today, or up to yesterday while
today has no such submission yet: the day is not over. A missed day resets
it, and the bonus with it. Computed from submissions on request, like
everything else here, so a check that ends with 0 points takes its day away.

Places: groupmates are ranked by rating; place = 1 + number of groupmates
with a strictly higher rating, so equal ratings share a place (6, 4, 4, 0 ->
places 1, 2, 2, 4). Groupmates may study different courses: each one counts
their own.

A student sees only their own data plus anonymous targets: the nearest higher
rating (equal ones are skipped) and the first place, how many points are
needed to overtake them (strictly more than the gap), and which steps of
their courses can bring those points: steps to complete first, in course
order, then steps with partial points to improve. The streak is left out of
the plan: it grows by itself only if the student keeps going.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from courses.models import Course, Module, Step
from courses.service import now
from models import User
from progress.schemas import (
    CoursePoints,
    MyRating,
    Opportunity,
    RankTarget,
    RatingRow,
    Streak,
)
from progress.service import (
    CourseProgress,
    StepState,
    course_progress,
    step_labels,
    studied_courses,
)
from submissions.models import IN_PROGRESS, Submission

STREAK_DAY_BONUS = 2
_COMPLETE = (StepState.NOT_STARTED, StepState.FAILED)


def _streak_days(days: set[date], today: date) -> int:
    day = today if today in days else today - timedelta(days=1)
    length = 0
    while day in days:
        length += 1
        day -= timedelta(days=1)
    return length


async def streaks(
    db: AsyncSession,
    user_ids: list[int],
    course_ids: list[int],
    at: datetime | None = None,
) -> dict[int, Streak]:
    tz = ZoneInfo(settings.timezone)
    today = (at or now()).astimezone(tz).date()
    rows = await db.execute(
        select(Submission.user_id, Submission.created_at)
        .join(Step, Step.id == Submission.step_id)
        .join(Module, Module.id == Step.module_id)
        .where(
            Submission.user_id.in_(user_ids),
            Module.course_id.in_(course_ids),
            or_(Submission.score > 0, Submission.status.in_(IN_PROGRESS)),
        )
    )
    days: dict[int, set[date]] = defaultdict(set)
    for user_id, created_at in rows:
        days[user_id].add(created_at.astimezone(tz).date())
    result = {}
    for user_id in user_ids:
        length = _streak_days(days[user_id], today)
        result[user_id] = Streak(
            days=length,
            bonus=STREAK_DAY_BONUS * length,
            active_today=today in days[user_id],
        )
    return result


@dataclass
class Rating:
    """Ratings of a set of students: a group, or one student without one."""

    students: list[User]
    courses: dict[int, list[Course]]
    # progress[user_id][course_id]
    progress: dict[int, dict[int, CourseProgress]]
    streaks: dict[int, Streak]

    def course_points(self, user_id: int) -> list[CoursePoints]:
        return [
            CoursePoints(
                course_id=c.id,
                title=c.title,
                points=self.progress[user_id][c.id].summary().points_earned,
            )
            for c in self.courses[user_id]
        ]

    def total(self, user_id: int) -> float:
        points = sum(c.points for c in self.course_points(user_id))
        return round(points + self.streaks[user_id].bonus, 2)

    def place(self, total: float) -> int:
        return 1 + sum(self.total(s.id) > total for s in self.students)

    def rows(self) -> list[RatingRow]:
        rows = [
            RatingRow(
                place=self.place(self.total(s.id)),
                student_id=s.id,
                username=s.username,
                name=s.name,
                surname=s.surname,
                patronymic=s.patronymic,
                total=self.total(s.id),
                courses=self.course_points(s.id),
                streak=self.streaks[s.id],
            )
            for s in self.students
        ]
        return sorted(rows, key=lambda r: (r.place, r.username))


async def rating_of(db: AsyncSession, students: list[User]) -> Rating:
    ids = [s.id for s in students]
    courses = await studied_courses(db, ids)
    progress: dict[int, dict[int, CourseProgress]] = {s.id: {} for s in students}
    by_course: dict[int, tuple[Course, list[User]]] = {}
    for s in students:
        for c in courses[s.id]:
            by_course.setdefault(c.id, (c, []))[1].append(s)
    for course, learners in by_course.values():
        for user_id, p in (await course_progress(db, course, learners)).items():
            progress[user_id][course.id] = p
    return Rating(students, courses, progress, await streaks(db, ids, list(by_course)))


async def opportunities(
    db: AsyncSession, courses: list[Course], progress: dict[int, CourseProgress]
) -> list[Opportunity]:
    """Where points can still be earned, in the order to go for them."""
    to_complete, to_improve = [], []
    for course in courses:
        p = progress[course.id]
        labels = await step_labels(db, course.id, [r.step for r in p.steps])

        def opportunity(r, action: str, course=course, labels=labels) -> Opportunity:
            return Opportunity(
                course_id=course.id,
                course_title=course.title,
                step_id=r.step.id,
                module_id=r.step.module_id,
                module_title=labels[r.step.id].module_title,
                position=labels[r.step.id].position,
                type=r.step.type,
                action=action,
                can_gain=round(r.step.max_score - r.earned, 2),
            )

        # Steps without points (theory) raise no rating: left out.
        open_ = [r for r in p.steps if r.step.max_score > 0 and r.attempts_left]
        to_complete += [
            opportunity(r, "complete") for r in open_ if r.state in _COMPLETE
        ]
        to_improve += [
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
    db: AsyncSession, user: User, rating: Rating, in_group: bool
) -> MyRating:
    mine = rating.total(user.id)
    opps = await opportunities(db, rating.courses[user.id], rating.progress[user.id])
    base = {
        "total": mine,
        "courses": rating.course_points(user.id),
        "streak": rating.streaks[user.id],
        "opportunities": opps,
    }
    if not in_group:
        return MyRating(**base)

    others = [rating.total(s.id) for s in rating.students if s.id != user.id]
    higher = [p for p in others if p > mine]
    next_place = None
    if higher:
        nearest = min(higher)
        next_place = _target(rating.place(nearest), nearest, mine, opps)
    return MyRating(
        **base,
        group_size=len(rating.students),
        place=rating.place(mine),
        tied_with=sum(p == mine for p in others),
        next_place=next_place,
        first_place=_target(1, max([mine, *others]), mine, opps),
    )
