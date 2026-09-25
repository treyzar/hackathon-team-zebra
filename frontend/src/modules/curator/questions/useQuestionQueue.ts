import { computed, ref } from "vue";

import { getApiErrorMessage } from "@/api/errors";
import { questionApi } from "./api";
import { questionsForFilter, selectedQuestionId } from "./presentation";
import type { QuestionFilter, QuestionUpdate, StaffQuestion } from "./types";

export function useQuestionQueue() {
  const questions = ref<StaffQuestion[]>([]);
  const filter = ref<QuestionFilter>("unanswered");
  const selectedId = ref<number | null>(null);
  const loading = ref(true);
  const saving = ref(false);
  const error = ref("");
  const saved = ref("");
  let loadVersion = 0;

  const unansweredCount = computed(
    () => questions.value.filter((item) => item.answer === null).length,
  );
  const visible = computed(() => questionsForFilter(questions.value, filter.value));
  const selected = computed(
    () => questions.value.find((item) => item.id === selectedId.value) ?? null,
  );
  const similar = computed(() =>
    selected.value
      ? questions.value.filter(
          (item) => item.step_id === selected.value?.step_id && item.id !== selected.value?.id,
        )
      : [],
  );

  async function load(): Promise<StaffQuestion[] | null> {
    const version = ++loadVersion;
    loading.value = true;
    error.value = "";
    saved.value = "";
    questions.value = [];
    selectedId.value = null;
    try {
      const items = await questionApi.all();
      if (version !== loadVersion) return null;
      questions.value = items;
      selectedId.value = selectedQuestionId(items, filter.value, null);
      return items;
    } catch (cause) {
      if (version === loadVersion) error.value = getApiErrorMessage(cause);
      return null;
    } finally {
      if (version === loadVersion) loading.value = false;
    }
  }

  function selectFilter(next: QuestionFilter): void {
    saved.value = "";
    error.value = "";
    filter.value = next;
    selectedId.value = selectedQuestionId(questions.value, next, selectedId.value);
  }

  function selectQuestion(id: number): void {
    saved.value = "";
    error.value = "";
    if (!visible.value.some((item) => item.id === id)) filter.value = "all";
    selectedId.value = id;
  }

  async function save(changes: QuestionUpdate): Promise<void> {
    const question = selected.value;
    if (!question?.can_answer || !Object.keys(changes).length || saving.value) return;
    saving.value = true;
    error.value = "";
    saved.value = "";
    try {
      const updated = await questionApi.update(question.id, changes);
      questions.value = questions.value.map((item) => (item.id === updated.id ? updated : item));
      if (selectedId.value === question.id && filter.value === "unanswered") {
        selectedId.value = selectedQuestionId(questions.value, filter.value, null);
      }
      saved.value = "Ответ сохранён.";
    } catch (cause) {
      error.value = getApiErrorMessage(cause);
    } finally {
      saving.value = false;
    }
  }

  function dispose(): void {
    ++loadVersion;
  }

  return {
    questions,
    filter,
    selectedId,
    loading,
    saving,
    error,
    saved,
    unansweredCount,
    visible,
    selected,
    similar,
    load,
    selectFilter,
    selectQuestion,
    save,
    dispose,
  };
}
