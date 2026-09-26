export interface AdminCourse {
  id: number;
  slug: string;
  title: string;
  description: Record<string, unknown>;
  is_published: boolean;
  step_access: string;
}

export interface EnrolledStudent {
  id: number;
  username: string;
  group_id: number | null;
}

export interface EnrollResult {
  enrolled: number[];
  already_enrolled: number[];
}

export interface GroupCourseCoverage {
  course: AdminCourse;
  enrolledStudentIds: number[];
  enrolledCount: number;
  studentsCount: number;
}

export interface CoursePoints {
  course_id: number;
  title: string;
  points: number;
}

/** A student's overall rating in the group: points of their courses plus a
 * streak bonus of 2 points per day in a row. */
export interface GroupRatingRow {
  place: number;
  student_id: number;
  username: string;
  name: string;
  surname: string;
  patronymic: string;
  total: number;
  courses: CoursePoints[];
  streak: { days: number; bonus: number; active_today: boolean };
}
