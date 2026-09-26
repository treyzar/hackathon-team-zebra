import type { RichDocument, RichNode } from "@/modules/student/courses/types";
import type { ChecklistItem, ReviewDetail, ReviewListItem, ReviewVerdict } from "./types";

export type GradeMode = "full" | "partial" | "revise";

export function selectedReviewId(items: ReviewListItem[], requested: number | null): number | null {
  return items.find((item) => item.id === requested)?.id ?? items[0]?.id ?? null;
}

export function nextReviewId(items: ReviewListItem[], completedId: number): number | null {
  const index = items.findIndex((item) => item.id === completedId);
  const remaining = items.filter((item) => item.id !== completedId);
  return remaining[Math.min(Math.max(index, 0), remaining.length - 1)]?.id ?? null;
}

export function studentLabel(item: ReviewListItem): string {
  const name = item.student_name.trim();
  const surname = item.student_surname.trim();
  return name && surname ? `${name} ${surname[0]}.` : item.student_username;
}

export function studentInitials(item: ReviewListItem): string {
  const letters = `${item.student_name[0] ?? ""}${item.student_surname[0] ?? ""}`;
  return letters.trim().toUpperCase() || item.student_username.slice(0, 2).toUpperCase();
}

export function waitingLabel(seconds: number | null): string {
  if (seconds === null) return "—";
  const minutes = Math.max(0, Math.floor(seconds / 60));
  if (minutes < 1) return "меньше минуты";
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const rest = minutes % 60;
  if (days) return `${days} д ${hours} ч`;
  if (hours) return rest ? `${hours} ч ${rest} мин` : `${hours} ч`;
  return `${minutes} мин`;
}

export function stepNumber(item: ReviewListItem): string {
  return item.task_number?.trim() || `#${item.step_id}`;
}

export function reviewTaskTitle(item: ReviewListItem): string {
  return item.task_title?.trim() || `Задание #${item.step_id}`;
}

export function attemptNumber(item: ReviewListItem): number {
  return Number.isInteger(item.attempts_before) && item.attempts_before >= 0
    ? item.attempts_before + 1
    : 1;
}

export function taskTitle(content: Record<string, unknown>, stepId: number): string {
  const first = taskDocument(content)?.content?.[0];
  if (first?.type === "heading" && first.attrs?.zebra_title === true) {
    const title = documentText(first).replace(/\s+/g, " ").trim();
    if (title) return title.slice(0, 100);
  }
  return `Задание #${stepId}`;
}

function richDocument(value: unknown): RichDocument | null {
  if (!value || typeof value !== "object") return null;
  const doc = value as RichDocument;
  return doc.type === "doc" && Array.isArray(doc.content) ? doc : null;
}

export function taskDocument(content: Record<string, unknown>): RichDocument | null {
  for (const key of ["question", "statement", "body"]) {
    const document = richDocument(content[key]);
    if (document) return document;
  }
  return null;
}

export function referenceDocument(key: Record<string, unknown>): RichDocument | null {
  return richDocument(key.reference);
}

export function taskBody(document: RichDocument | null): RichDocument | null {
  if (!document) return null;
  const [first, ...rest] = document.content ?? [];
  const attrs = first?.attrs;
  return first?.type === "heading" && attrs?.zebra_title === true
    ? { ...document, content: rest }
    : document;
}

export function answerFiles(answer: Record<string, unknown>): number[] {
  return Array.isArray(answer.files)
    ? answer.files.filter((id): id is number => Number.isInteger(id) && id > 0)
    : [];
}

export function choiceLabels(ids: unknown, content: Record<string, unknown>): string[] {
  const selected = Array.isArray(ids) ? ids : ids === undefined ? [] : [ids];
  const options = Array.isArray(content.options) ? content.options : [];
  return selected.map((id) => {
    const option = options.find(
      (value) => value && typeof value === "object" && (value as { id?: unknown }).id === id,
    ) as { text?: unknown } | undefined;
    return typeof option?.text === "string" ? option.text : String(id);
  });
}

export function referenceChoices(detail: ReviewDetail): string[] {
  return choiceLabels(detail.answer_key.correct, detail.content);
}

export function submittedChoices(detail: ReviewDetail): string[] {
  return choiceLabels(detail.answer.option_ids ?? detail.answer.option_id, detail.content);
}

export function verdictFor(
  mode: GradeMode,
  score: number,
  maxScore: number,
  comment: string,
): ReviewVerdict {
  return {
    verdict: mode === "revise" ? "rejected" : "accepted",
    score: mode === "full" ? maxScore : mode === "revise" ? 0 : score,
    comment: comment.trim() || null,
  };
}

/** Criteria of the step's checklist; empty when the step has none. */
export function reviewChecklist(detail: ReviewDetail): ChecklistItem[] {
  const items = detail.settings.checklist;
  return Array.isArray(items) ? (items as ChecklistItem[]) : [];
}

export function checklistScore(items: ChecklistItem[], checked: string[]): number {
  const met = items.filter((item) => checked.includes(item.id));
  return Math.round(met.reduce((sum, item) => sum + item.points, 0) * 100) / 100;
}

/** The score follows from the met criteria, so none is sent. */
export function checklistVerdict(
  accepted: boolean,
  checked: string[],
  comment: string,
): ReviewVerdict {
  return {
    verdict: accepted ? "accepted" : "rejected",
    checked,
    comment: comment.trim() || null,
  };
}

export function plainText(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function referenceText(detail: ReviewDetail): string {
  if (typeof detail.answer_key.reference === "string") return detail.answer_key.reference;
  if (typeof detail.answer_key.reference_solution === "string")
    return detail.answer_key.reference_solution;
  if (Array.isArray(detail.answer_key.accepted))
    return detail.answer_key.accepted
      .filter((entry): entry is string => typeof entry === "string")
      .join("; ");
  return plainText(detail.answer_key.value);
}

export function documentText(node: RichNode): string {
  return node.type === "text"
    ? (node.text ?? "")
    : (node.content ?? []).map(documentText).join(" ");
}
