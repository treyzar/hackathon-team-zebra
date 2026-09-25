export type StepType = "theory" | "single_choice" | "multiple_choice" | "free_text" | "programming";
export type StepAccess = "all" | "sequential";
export type Grading = "none" | "auto" | "tests" | "tests_and_review" | "manual";
export type ShowAnswer = "never" | "after_wrong" | "after_attempts_exhausted" | "after_solved";
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

export type ProgrammingLanguage = "python3" | "javascript" | "cpp" | "csharp" | "go" | "pascal";

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
  step_id: number;
  module_id: number;
  module_title: string;
  position: number;
  type: string;
  action: string;
  can_gain: number;
}

export interface MyRating {
  course_id: number;
  group_size: number;
  points: number;
  place: number;
  tied_with: number;
  next_place: RankTarget | null;
  first_place: RankTarget;
  opportunities: RatingOpportunity[];
}
