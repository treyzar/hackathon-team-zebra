export type QuestionVisibility = "private" | "group" | "course";

export interface StaffQuestion {
  id: number;
  step_id: number;
  course_id: number;
  course_title: string;
  module_title: string;
  author_id: number;
  author_username: string;
  author_name: string;
  author_surname: string;
  author_patronymic: string;
  text: string;
  created_at: string;
  answer: string | null;
  answered_by: number | null;
  answered_at: string | null;
  visibility: QuestionVisibility;
  group_id: number | null;
  can_answer: boolean;
  waiting_seconds: number | null;
}

export interface QuestionUpdate {
  answer?: string;
  visibility?: QuestionVisibility;
}
