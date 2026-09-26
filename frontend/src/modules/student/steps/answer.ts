import type { ProgrammingLanguage } from "../../languages";
import type { FreeTextContent, StepType } from "@/modules/student/courses/types";

export interface AnswerDraft {
  selected: string[];
  text: string;
  files: number[];
  code: string;
  language: ProgrammingLanguage;
}

function buildFreeTextAnswer(
  content: Record<string, unknown>,
  draft: AnswerDraft,
): Record<string, unknown> | null {
  const rules = content as unknown as FreeTextContent;
  const text = draft.text.trim();

  if (rules.require_text && !text) return null;
  if (draft.files.length < rules.min_files) return null;
  if (!text && !draft.files.length) return null;

  return { text: draft.text, files: draft.files };
}

export function buildAnswer(
  type: StepType,
  content: Record<string, unknown>,
  draft: AnswerDraft,
): Record<string, unknown> | null {
  switch (type) {
    case "theory":
      return {};
    case "single_choice":
      return draft.selected[0] ? { option_id: draft.selected[0] } : null;
    case "multiple_choice":
      return draft.selected.length ? { option_ids: draft.selected } : null;
    case "free_text":
      return buildFreeTextAnswer(content, draft);
    case "programming":
      return draft.code.trim() ? { code: draft.code, language: draft.language } : null;
    case "number": {
      const value = draft.text.trim();
      return value ? { value } : null;
    }
    case "short_text": {
      const value = draft.text.trim();
      return value ? { text: value } : null;
    }
  }
}
