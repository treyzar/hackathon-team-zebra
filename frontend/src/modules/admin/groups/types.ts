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
