import type { StepType } from "@/modules/student/courses/types";

export interface ReviewListItem {
  id: number;
  status: string;
  created_at: string;
  auto_score: number | null;
  score: number | null;
  student_id: number;
  student_username: string;
  student_name: string;
  student_surname: string;
  student_patronymic: string;
  step_id: number;
  step_type: StepType;
  max_score: number;
  course_id: number;
  task_title?: string;
  task_number?: string;
  course_title: string;
  module_title: string;
  deadline_due_at: string | null;
  is_late: boolean;
  waiting_seconds: number | null;
  attempts_before: number;
}

export interface CourseQueue {
  course_id: number;
  course_title: string;
  total: number;
  late: number;
  oldest_at: string;
  longest_waiting_seconds: number;
  submissions: ReviewListItem[];
}

export interface ReviewDetail extends ReviewListItem {
  answer: Record<string, unknown>;
  result_details: Record<string, unknown>;
  is_outdated: boolean;
  review_comment: string | null;
  reviewer_id: number | null;
  reviewed_at: string | null;
  content: Record<string, unknown>;
  answer_key: Record<string, unknown>;
  settings: Record<string, unknown>;
}

export interface ReviewVerdict {
  verdict: "accepted" | "rejected";
  score: number;
  comment: string | null;
}

export interface ReviewFile {
  filename: string;
  mime: string;
  download_url: string;
}
