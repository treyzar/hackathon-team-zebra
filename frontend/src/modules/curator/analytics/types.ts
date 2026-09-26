export interface AnalyticsGroup {
  id: number;
  name: string;
  curator_id: number | null;
}

export interface ModuleStats {
  module_id: number;
  title: string;
  students_passed: number;
  students_in_progress: number;
  students_not_started: number;
  first_attempt_percent: number | null;
  avg_attempts: number | null;
  returns: number;
}

export interface StudentInfo {
  student_id: number;
  username: string;
  name: string;
  surname: string;
  patronymic: string;
}

export interface StudentModule {
  module_id: number;
  state: "passed" | "in_progress" | "not_started";
  steps_total: number;
  steps_completed: number;
  has_submissions: boolean;
  has_unresolved_return: boolean;
}

export interface StudentAnalytics extends StudentInfo {
  lag: { status: "on_track" | "slowed" | "falling_behind" };
  last_submission_at: string | null;
  modules: StudentModule[];
}

export interface CourseAnalytics {
  course_id: number;
  group_id: number;
  students_total: number;
  modules: ModuleStats[];
  students: StudentAnalytics[];
}

export interface StepColumn {
  step_id: number;
  position: number;
  type: string;
  title: string;
  max_score: number;
}

export interface StepCell {
  step_id: number;
  state: "not_started" | "checking" | "failed" | "attempts_exhausted" | "partial" | "passed";
  earned: number;
  max_score: number;
  completed: boolean;
  attempts: number;
  first_attempt_solved: boolean | null;
  has_unresolved_return: boolean;
  last_submission_at: string | null;
}

export interface StudentSteps extends StudentInfo {
  steps: StepCell[];
}

export interface ModuleAnalytics {
  course_id: number;
  module: ModuleStats;
  steps: StepColumn[];
  students: StudentSteps[];
}
