import type { RichText, StepType } from "./types";

export const stepTypeLabels: Record<StepType, string> = {
  theory: "Теория",
  single_choice: "Контрольный вопрос",
  multiple_choice: "Контрольный вопрос",
  free_text: "Проект",
  programming: "Задача с тестами",
};

export function textToDoc(value: string): RichText {
  return {
    type: "doc",
    content: value.split("\n").map((line) => ({
      type: "paragraph",
      content: line ? [{ type: "text", text: line }] : [],
    })),
  };
}

export function docToText(value: unknown): string {
  if (!value || typeof value !== "object") return "";
  const doc = value as { content?: unknown[] };
  return (doc.content ?? [])
    .map((node) => {
      const paragraph = node as { content?: { text?: string }[] };
      return (paragraph.content ?? []).map((part) => part.text ?? "").join("");
    })
    .join("\n");
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}
