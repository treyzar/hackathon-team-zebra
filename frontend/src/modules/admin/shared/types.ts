import type { UserResponse, UserRole } from "@/api/http";

export type RichText = { type: "doc"; content: Record<string, unknown>[] };
export type StepType = "theory" | "single_choice" | "multiple_choice" | "free_text" | "programming";
export type StepAccess = "all" | "sequential";

export interface Course {
  id: number;
  slug: string;
  title: string;
  description: RichText;
  is_published: boolean;
  step_access: StepAccess;
}

export interface StepSummary {
  id: number;
  type: StepType;
  position: number;
  is_hidden: boolean;
  max_score: number;
  revision_number: number;
}

export interface Module {
  id: number;
  title: string;
  position: number;
  steps: StepSummary[];
}

export interface CourseTree extends Course {
  modules: Module[];
}

export interface Revision {
  number: number;
  created_at: string;
  author_id: number | null;
  comment: string | null;
  is_breaking: boolean;
  max_score: number;
  schema_version: number;
  content: Record<string, unknown>;
  answer_key: Record<string, unknown>;
  settings: Record<string, unknown>;
}

export type RevisionSummary = Pick<
  Revision,
  "number" | "created_at" | "author_id" | "comment" | "is_breaking"
>;

export interface Step {
  id: number;
  module_id: number;
  type: StepType;
  position: number;
  is_hidden: boolean;
  revision: Revision;
}

export interface Group {
  id: number;
  name: string;
  curator_id: number | null;
  students_count: number;
}

export interface StepPayload {
  type: StepType;
  max_score: number;
  content: Record<string, unknown>;
  answer_key: Record<string, unknown>;
  settings: Record<string, unknown>;
}

export interface StepSave {
  payload: StepPayload;
  comment?: string;
  is_breaking?: boolean;
  base_revision?: number;
}

export type AdminUser = UserResponse;
export type AdminRole = UserRole;
