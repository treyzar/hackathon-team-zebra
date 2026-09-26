export type LagStatus = "on_track" | "slowed" | "falling_behind";

export interface LearnerCourse {
  course_id: number;
  title: string;
  status: LagStatus;
  overdue_steps: number;
}

export interface Learner {
  student_id: number;
  username: string;
  name: string;
  surname: string;
  patronymic: string;
  // The worst status over the student's courses; null without courses.
  status: LagStatus | null;
  courses: LearnerCourse[];
}

export interface LearnerGroup {
  group_id: number;
  name: string;
  students: Learner[];
}
