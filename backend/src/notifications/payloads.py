from datetime import datetime

from pydantic import BaseModel

from notifications.models import NotificationType


class DeadlineApproachingPayload(BaseModel):
    step_id: int
    course_id: int
    deadline: datetime
    hours_left: int


class DeadlinePassedPayload(BaseModel):
    step_id: int
    course_id: int
    deadline: datetime


class DeadlineChangedPayload(BaseModel):
    step_id: int
    course_id: int
    deadline: datetime
    previous: datetime | None = None


class SubmissionReviewedPayload(BaseModel):
    submission_id: int
    step_id: int
    course_id: int
    verdict: str
    score: float
    max_score: int


class SubmissionPendingReviewPayload(BaseModel):
    submission_id: int
    step_id: int
    student_id: int
    student_username: str


class SubmissionQueueReminderPayload(BaseModel):
    pending: int


class StepSolvedPayload(BaseModel):
    step_id: int
    course_id: int
    score: float
    max_score: int


class StepUnlockedPayload(BaseModel):
    step_id: int
    course_id: int
    title: str


class StepBreakingChangePayload(BaseModel):
    step_id: int
    course_id: int
    outdated: int


class CoursePayload(BaseModel):
    course_id: int
    course_title: str


class GroupPayload(BaseModel):
    group_id: int
    group_name: str


class HelloPayload(BaseModel):
    username: str


class RoleChangedPayload(BaseModel):
    role: str


PAYLOADS: dict[NotificationType, type[BaseModel]] = {
    NotificationType.DEADLINE_APPROACHING: DeadlineApproachingPayload,
    NotificationType.DEADLINE_PASSED: DeadlinePassedPayload,
    NotificationType.DEADLINE_CHANGED: DeadlineChangedPayload,
    NotificationType.SUBMISSION_REVIEWED: SubmissionReviewedPayload,
    NotificationType.SUBMISSION_PENDING_REVIEW: SubmissionPendingReviewPayload,
    NotificationType.SUBMISSION_QUEUE_REMINDER: SubmissionQueueReminderPayload,
    NotificationType.STEP_SOLVED: StepSolvedPayload,
    NotificationType.STEP_UNLOCKED: StepUnlockedPayload,
    NotificationType.STEP_BREAKING_CHANGE: StepBreakingChangePayload,
    NotificationType.COURSE_COMPLETED: CoursePayload,
    NotificationType.COURSE_PUBLISHED: CoursePayload,
    NotificationType.COURSE_ATTENTION_NEEDED: CoursePayload,
    NotificationType.ADDED_TO_GROUP: GroupPayload,
    NotificationType.MOVED_TO_GROUP: GroupPayload,
    NotificationType.ASSIGNED_GROUP: GroupPayload,
    NotificationType.HELLO: HelloPayload,
    NotificationType.ROLE_CHANGED: RoleChangedPayload,
}