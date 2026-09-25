import type { QuestionUpdate, QuestionVisibility, StaffQuestion } from "./types";

export function questionAuthor(question: StaffQuestion): string {
  const name = question.author_name.trim();
  const surname = question.author_surname.trim();
  return name && surname ? `${name} ${surname[0]}.` : question.author_username;
}

export function questionAge(question: StaffQuestion, now = Date.now()): string {
  const seconds =
    question.waiting_seconds ?? Math.max(0, (now - Date.parse(question.created_at)) / 1000);
  if (!Number.isFinite(seconds)) return "—";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч`;
  return `${Math.floor(hours / 24)} д`;
}

export function questionUpdate(
  question: StaffQuestion,
  answer: string,
  visibility: QuestionVisibility,
): QuestionUpdate {
  const changes: QuestionUpdate = {};
  const trimmed = answer.trim();
  if (trimmed !== (question.answer ?? "")) changes.answer = trimmed;
  if (visibility !== question.visibility) changes.visibility = visibility;
  return changes;
}
