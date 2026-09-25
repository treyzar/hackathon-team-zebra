import type { FreeTextContent, StepType } from "@/modules/student/courses/types";

export interface AnswerDraft {
  selected: string[];
  text: string;
  files: number[];
  code: string;
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
    case "free_text": {
      const rules = content as unknown as FreeTextContent;
      if (
        (rules.require_text && !draft.text.trim()) ||
        draft.files.length < rules.min_files ||
        (!draft.text.trim() && !draft.files.length)
      )
        return null;
      return { text: draft.text, files: draft.files };
    }
    case "programming":
      return draft.code.trim() ? { code: draft.code, language: "python3" } : null;
  }
}
