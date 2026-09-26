import type { ProgrammingLanguage } from "../../languages";

export type QuestionVisibility = "private" | "group" | "course";
export type StepAccess = "all" | "sequential";
export type Grading = "none" | "auto" | "tests" | "tests_and_review" | "manual";
export type ShowAnswer = "never" | "after_wrong" | "after_attempts_exhausted" | "after_solved";
export type StepType =
  | "theory"
  | "single_choice"
  | "multiple_choice"
  | "free_text"
  | "programming"
  | "number"
  | "short_text";

export type SubmissionStatus =
  | "queued"
  | "running"
  | "pending_review"
  | "correct"
  | "partial"
  | "wrong"
  | "accepted"
  | "rejected"
  | "error";

export interface NumberContent {
  question: RichDocument;
  kind: "integer" | "decimal";
  precision: number;
}

export interface ShortTextContent {
  question: RichDocument;
}

export interface StudentQuestion {
  id: number;
  step_id: number;
  text: string;
  created_at: string;
  is_mine: boolean;
  visibility: QuestionVisibility;
  answer: string | null;
  answered_at: string | null;
}
export interface Progress {
  steps_total: number;
  steps_completed: number;
  steps_passed: number;
  points_earned: number;
  points_max: number;
  percent: number;
  next_step_id: number | null;
}

export interface StepProgress {
  state: string;
  earned: number;
  max_score: number;
  graded_by: string | null;
  best_submission_id: number | null;
  completed: boolean;
  from_previous_version: boolean;
}

export interface Deadline {
  due_at: string;
  inherited: boolean;
  source_step_id: number;
}

export interface CourseListItem {
  id: number;
  slug: string;
  title: string;
  progress: Progress;
}

export interface StepSummary {
  id: number;
  type: StepType;
  max_score: number;
  progress: StepProgress;
  locked: boolean;
  deadline: Deadline | null;
}

export interface CourseModule {
  id: number;
  title: string;
  progress: Progress;
  steps: StepSummary[];
}

export interface Course extends CourseListItem {
  description: RichDocument;
  step_access: StepAccess;
  modules: CourseModule[];
}

export interface RichDocument {
  type: string;
  content?: RichNode[];
}

export interface RichNode {
  type?: string;
  text?: string;
  attrs?: Record<string, unknown>;
  marks?: { type?: string; attrs?: Record<string, unknown> }[];
  content?: RichNode[];
}

export interface ChoiceContent {
  question: RichDocument;
  options: { id: string; text: string }[];
}

export interface FreeTextContent {
  question: RichDocument;
  require_text: boolean;
  min_files: number;
  max_files: number;
  allowed_mime: string[];
}

export interface ProgrammingContent {
  statement: RichDocument;
  languages: ProgrammingLanguage[];
  template: string;
  time_limit_ms: number;
  memory_limit_mb: number;
  samples: { input: string; output: string }[];
}

export interface StudentStep {
  id: number;
  course_id: number;
  module_id: number;
  type: StepType;
  max_score: number;
  content: Record<string, unknown>;
  grading: Grading;
  max_attempts: number | null;
  show_answer: ShowAnswer;
  attempts_used: number;
  progress: StepProgress;
  answer_available: boolean;
  can_submit: boolean;
  submit_block_reason: string | null;
  deadline: Deadline | null;
}

export interface Submission {
  id: number;
  step_id: number;
  status: SubmissionStatus;
  score: number | null;
  auto_score: number | null;
  answer: Record<string, unknown>;
  result_details: Record<string, unknown>;
  is_outdated: boolean;
  review_comment: string | null;
  reviewed_at: string | null;
  created_at: string;
  deadline_due_at: string | null;
  is_late: boolean;
  explanation: Record<string, unknown> | null;
}

export interface Lag {
  status: string;
  overdue: Array<{
    step_id: number;
    module_id: number;
    module_title: string;
    position: number;
    type: string;
    due_at: string;
    days_overdue: number;
    state: string;
  }>;
}

export interface ModuleProgress extends Progress {
  module_id: number;
  title: string;
}

export interface StepProgressDetail extends StepProgress {
  step_id: number;
  module_id: number;
  type: string;
  attempts_used: number;
  max_attempts: number | null;
}

export interface CourseProgress extends Progress {
  course_id: number;
  lag: Lag;
  modules: ModuleProgress[];
  steps: StepProgressDetail[];
}

export interface RankTarget {
  place: number;
  points: number;
  gap: number | null;
  plan: number[];
  reachable: boolean;
}

export interface RatingOpportunity {
  course_id: number;
  course_title: string;
  step_id: number;
  module_id: number;
  module_title: string;
  position: number;
  type: string;
  action: string;
  can_gain: number;
}

export interface CoursePoints {
  course_id: number;
  title: string;
  points: number;
}

export interface Streak {
  days: number;
  bonus: number;
  // False: nothing counted today yet; the streak ends unless something is sent.
  active_today: boolean;
}

/** Overall rating: points of every course plus the streak bonus. Group
 * fields are null for a student without a group. */
export interface MyRating {
  total: number;
  courses: CoursePoints[];
  streak: Streak;
  group_size: number | null;
  place: number | null;
  tied_with: number | null;
  next_place: RankTarget | null;
  first_place: RankTarget | null;
  opportunities: RatingOpportunity[];
}

export type StudentNotificationType =
  | "deadline_approaching"
  | "deadline_passed"
  | "deadline_changed"
  | "submission_reviewed"
  | "submission_pending_review"
  | "submission_queue_reminder"
  | "step_solved"
  | "step_unlocked"
  | "step_breaking_change"
  | "course_completed"
  | "course_published"
  | "course_attention_needed"
  | "added_to_group"
  | "moved_to_group"
  | "assigned_group"
  | "hello"
  | "role_changed";

export interface StudentNotification {
  id: number;
  type: StudentNotificationType;
  severity: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}
