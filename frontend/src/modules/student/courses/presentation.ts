import type { RichDocument, RichNode, StepType } from "./types";

export const stepLabels: Record<StepType, string> = {
  theory: "Теория",
  single_choice: "Вопрос с одним ответом",
  multiple_choice: "Вопрос с несколькими ответами",
  free_text: "Задание с ответом",
  programming: "Задача с кодом",
};

/** Russian noun agreement: 1 балл, 2 балла, 5 баллов, 11 баллов, 21 балл. */
export function pointsWord(count: number): string {
  const tens = Math.abs(count) % 100;
  const units = tens % 10;
  if (tens >= 11 && tens <= 14) return "баллов";
  if (units === 1) return "балл";
  if (units >= 2 && units <= 4) return "балла";
  return "баллов";
}

export function pointsText(count: number): string {
  return `${count} ${pointsWord(count)}`;
}

export function progressText(completed: number, total: number): string {
  return total ? `${completed} из ${total} шагов` : "Шагов пока нет";
}

export function stepDocument(
  type: StepType,
  content: Record<string, unknown>,
): RichDocument | null {
  const key = type === "theory" ? "body" : type === "programming" ? "statement" : "question";
  const value = content[key];
  return value && typeof value === "object" && (value as RichDocument).type === "doc"
    ? (value as RichDocument)
    : null;
}

function nodeText(node: RichNode): string {
  return node.type === "text" ? (node.text ?? "") : (node.content ?? []).map(nodeText).join(" ");
}

export function documentTitle(doc: RichDocument | null, fallback: string): string {
  if (!doc) return fallback;
  const heading = doc.content?.find((node) => node.type === "heading");
  const first = heading ?? doc.content?.find((node) => nodeText(node).trim());
  return first ? nodeText(first).replace(/\s+/g, " ").trim().slice(0, 100) || fallback : fallback;
}

export function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })
      .response;
    if (response?.status === 404) return "Курс или шаг не найден.";
    if (response?.status === 403) return "Этот материал пока недоступен.";
    if (typeof response?.data?.detail === "string") return response.data.detail;
  }
  return "Не удалось загрузить данные. Попробуйте ещё раз.";
}

export function submissionLabel(status: string): string {
  switch (status) {
    case "queued":
      return "Ожидает проверки";
    case "running":
      return "Проверяется";
    case "pending_review":
      return "На проверке у куратора";
    case "correct":
    case "accepted":
      return "Зачтено";
    case "partial":
      return "Частично верно";
    case "wrong":
    case "rejected":
      return "Пока не то";
    case "error":
      return "Ошибка проверки";
    default:
      return status;
  }
}

export function blockReason(reason: string | null): string {
  switch (reason) {
    case "The previous submission is still being checked":
      return "Предыдущее решение ещё проверяется.";
    case "The step is already solved with the maximum score":
      return "Шаг уже выполнен на максимальный балл.";
    case "No attempts left":
      return "Попытки закончились.";
    default:
      return reason ?? "";
  }
}
