import { computed, onBeforeUnmount, onMounted, ref, type Ref } from "vue";
import {
  getAnswer,
  getSubmission,
  getSubmissions,
  submitAnswer,
  uploadSubmissionFile,
} from "@/modules/student/courses/api";
import {
  documentTitle,
  errorMessage,
  stepDocument,
  stepLabels,
} from "@/modules/student/courses/presentation";
import type {
  ChoiceContent,
  FreeTextContent,
  ProgrammingContent,
  RichDocument,
  StudentStep,
  Submission,
} from "@/modules/student/courses/types";
import { buildAnswer } from "./answer";

export interface AttachedFile {
  id: number;
  name: string;
}

interface UseStepPlayerOptions {
  step: Ref<StudentStep>;
  onRefresh: () => void;
}

const ACTIVE_STATUSES = ["queued", "running"];

export function useStepPlayer({ step, onRefresh }: UseStepPlayerOptions) {
  const selected = ref<string[]>([]);
  const answerText = ref("");
  const code = ref("");
  const files = ref<AttachedFile[]>([]);
  const submissions = ref<Submission[]>([]);
  const revealed = ref<Record<string, unknown> | null>(null);

  const loading = ref(true);
  const saving = ref(false);
  const uploading = ref(false);
  const error = ref("");

  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let active = true;

  const document = computed(() => stepDocument(step.value.type, step.value.content));
  const title = computed(() => documentTitle(document.value, stepLabels[step.value.type]));
  const bodyDocument = computed<RichDocument | null>(() => {
    if (!document.value) return null;
    const first = document.value.content?.[0];
    return first?.type === "heading"
      ? { ...document.value, content: document.value.content?.slice(1) }
      : document.value;
  });

  const choice = computed(() => step.value.content as unknown as ChoiceContent);
  const freeText = computed(() => step.value.content as unknown as FreeTextContent);
  const programming = computed(() => step.value.content as unknown as ProgrammingContent);

  const latest = computed(() => submissions.value[0] ?? null);
  const blocked = computed(
    () => loading.value || saving.value || uploading.value || !step.value.can_submit,
  );
  const remaining = computed(() =>
    step.value.max_attempts == null
      ? null
      : Math.max(0, step.value.max_attempts - step.value.attempts_used),
  );

  const correctChoices = computed(() => {
    if (!revealed.value) return [];
    if (typeof revealed.value.correct === "string") return [revealed.value.correct];
    return Array.isArray(revealed.value.correct) ? (revealed.value.correct as string[]) : [];
  });

  const referenceSolution = computed(() =>
    typeof revealed.value?.reference_solution === "string"
      ? revealed.value.reference_solution
      : "",
  );

  const referenceDocument = computed(() => {
    const value = revealed.value?.reference;
    return value && typeof value === "object" && (value as RichDocument).type === "doc"
      ? (value as RichDocument)
      : null;
  });

  function restoreAnswer(submission?: Submission): void {
    const answer = submission?.answer;

    if (step.value.type === "programming") {
      code.value =
        typeof answer?.code === "string" ? answer.code : (programming.value.template ?? "");
    }

    if (step.value.type === "single_choice" && typeof answer?.option_id === "string") {
      selected.value = [answer.option_id];
    }

    if (step.value.type === "multiple_choice" && Array.isArray(answer?.option_ids)) {
      selected.value = answer.option_ids as string[];
    }

    if (step.value.type === "free_text") {
      answerText.value = typeof answer?.text === "string" ? answer.text : "";
      files.value = Array.isArray(answer?.files)
        ? (answer.files as number[]).map((id) => ({ id, name: `Файл #${id}` }))
        : [];
    }
  }

  function clearPollTimer(): void {
    if (!pollTimer) return;
    clearTimeout(pollTimer);
    pollTimer = null;
  }

  function schedulePoll(): void {
    clearPollTimer();
    if (!latest.value || !ACTIVE_STATUSES.includes(latest.value.status)) return;

    pollTimer = setTimeout(async () => {
      if (!active || !latest.value) return;

      try {
        const result = await getSubmission(latest.value.id);
        if (!active) return;

        submissions.value = [result, ...submissions.value.slice(1)];
        if (!ACTIVE_STATUSES.includes(result.status)) onRefresh();
        schedulePoll();
      } catch {
        if (active) pollTimer = setTimeout(schedulePoll, 5000);
      }
    }, 2500);
  }

  async function loadSubmissions(): Promise<void> {
    loading.value = true;
    try {
      submissions.value = await getSubmissions(step.value.id);
      restoreAnswer(submissions.value[0]);
      schedulePoll();
    } catch (cause) {
      error.value = errorMessage(cause);
    } finally {
      loading.value = false;
    }
  }

  function toggleOption(id: string): void {
    if (step.value.type === "single_choice") {
      selected.value = [id];
      return;
    }

    selected.value = selected.value.includes(id)
      ? selected.value.filter((item) => item !== id)
      : [...selected.value, id];
  }

  function removeFile(id: number): void {
    files.value = files.value.filter((file) => file.id !== id);
  }

  async function addFiles(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const picked = [...(input.files ?? [])];
    input.value = "";

    if (files.value.length + picked.length > freeText.value.max_files) {
      error.value = `Можно приложить не больше ${freeText.value.max_files} файлов.`;
      return;
    }

    error.value = "";
    uploading.value = true;

    try {
      for (const file of picked) {
        if (
          freeText.value.allowed_mime.length &&
          !freeText.value.allowed_mime.includes(file.type)
        ) {
          throw new Error(`Формат файла «${file.name}» не разрешён.`);
        }

        files.value.push({ id: await uploadSubmissionFile(file), name: file.name });
      }
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : errorMessage(cause);
    } finally {
      uploading.value = false;
    }
  }

  async function submit(): Promise<void> {
    if (blocked.value) return;

    const answer = buildAnswer(step.value.type, step.value.content, {
      selected: selected.value,
      text: answerText.value,
      files: files.value.map((file) => file.id),
      code: code.value,
    });

    if (!answer) {
      error.value =
        step.value.type === "free_text"
          ? "Заполните ответ и приложите необходимые файлы."
          : "Введите ответ перед отправкой.";
      return;
    }

    error.value = "";
    saving.value = true;

    try {
      const submission = await submitAnswer(step.value.id, answer);
      submissions.value = [submission, ...submissions.value];
      onRefresh();
      schedulePoll();
    } catch (cause) {
      error.value = errorMessage(cause);
    } finally {
      saving.value = false;
    }
  }

  async function revealAnswer(): Promise<void> {
    error.value = "";
    try {
      revealed.value = await getAnswer(step.value.id);
    } catch (cause) {
      error.value = errorMessage(cause);
    }
  }

  onMounted(loadSubmissions);
  onBeforeUnmount(() => {
    active = false;
    clearPollTimer();
  });

  return {
    title,
    bodyDocument,
    choice,
    freeText,
    programming,
    selected,
    answerText,
    code,
    files,
    submissions,
    revealed,
    loading,
    saving,
    uploading,
    error,
    latest,
    blocked,
    remaining,
    correctChoices,
    referenceSolution,
    referenceDocument,
    toggleOption,
    addFiles,
    removeFile,
    submit,
    revealAnswer,
  };
}
