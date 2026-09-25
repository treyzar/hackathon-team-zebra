export type StepType = "theory" | "single_choice" | "multiple_choice" | "free_text" | "programming";

export interface Progress {
  steps_total: number;
  steps_completed: number;
  steps_passed: number;
  points_earned: number;
  points_max: number;
  percent: number;
  next_step_id?: number | null;
}

export interface StepProgress {
  state: "not_started" | "checking" | "failed" | "attempts_exhausted" | "partial" | "passed";
  earned: number;
  max_score: number;
  completed: boolean;
  from_previous_version: boolean;
}

export interface Deadline {
  due_at: string;
  inherited: boolean;
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
  step_access: "all" | "sequential";
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
  language: "python3";
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
  grading: string;
  max_attempts: number | null;
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
  status:
    | "queued"
    | "running"
    | "pending_review"
    | "correct"
    | "partial"
    | "wrong"
    | "accepted"
    | "rejected"
    | "error";
  score: number | null;
  answer: Record<string, unknown>;
  result_details: Record<string, unknown>;
  review_comment: string | null;
  created_at: string;
  is_late: boolean;
  explanation: Record<string, unknown> | null;
}
