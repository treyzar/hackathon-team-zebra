import type { RichDocument, RichNode } from "@/modules/student/courses/types";

export function richDocument(value: unknown): RichDocument | null {
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

function documentText(node: RichNode): string {
  return node.type === "text"
    ? (node.text ?? "")
    : (node.content ?? []).map(documentText).join(" ");
}

export function taskTitle(content: Record<string, unknown>, stepId: number): string {
  const nodes = taskDocument(content)?.content ?? [];
  const first =
    nodes.find((node) => node.type === "heading" && node.attrs?.zebra_title === true) ??
    nodes.find((node) => node.type === "heading") ??
    nodes.find((node) => documentText(node).trim());
  const title = first ? documentText(first).replace(/\s+/g, " ").trim() : "";
  if (title) return title.slice(0, 100);
  return `Задание #${stepId}`;
}
