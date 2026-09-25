import { computed, onBeforeUnmount, ref, watch, type Ref } from "vue";
import { studentCourseApi } from "../api";
import { documentTitle, errorMessage, stepDocument, stepLabels } from "../presentation";
import type { Course, StudentStep } from "../types";

export function useCourseWorkspace(courseId: Ref<number>, stepId: Ref<number | undefined>) {
  const course = ref<Course | null>(null);
  const step = ref<StudentStep | null>(null);
  const titles = ref(new Map<number, string>());
  const loading = ref(true);
  const stepLoading = ref(false);
  const error = ref("");
  let courseVersion = 0;
  let stepVersion = 0;
  let disposed = false;

  const selectedSummary = computed(() =>
    course.value?.modules
      .flatMap((module) => module.steps)
      .find((item) => item.id === stepId.value),
  );

  const stepNumber = computed(() => {
    if (!course.value || !stepId.value) return "";
    for (const [moduleIndex, module] of course.value.modules.entries()) {
      const index = module.steps.findIndex((item) => item.id === stepId.value);
      if (index !== -1) return `${moduleIndex + 1}.${index + 1}`;
    }
    return "";
  });

  async function loadTitles(snapshot: Course, version: number): Promise<void> {
    const waiting = snapshot.modules
      .flatMap((module) => module.steps)
      .filter((item) => !item.locked && !titles.value.has(item.id));
    let cursor = 0;
    await Promise.all(
      Array.from({ length: Math.min(6, waiting.length) }, async () => {
        while (cursor < waiting.length && version === courseVersion && !disposed) {
          const item = waiting[cursor++];
          if (!item) continue;
          try {
            const detail = await studentCourseApi.getStep(item.id);
            if (version !== courseVersion || disposed) return;
            const next = new Map(titles.value);
            next.set(
              item.id,
              documentTitle(stepDocument(detail.type, detail.content), stepLabels[detail.type]),
            );
            titles.value = next;
          } catch {
            // Summary titles are optional enhancement: navigation remains usable by step type.
          }
        }
      }),
    );
  }

  async function loadSelectedStep(snapshot = course.value): Promise<void> {
    const version = ++stepVersion;
    step.value = null;
    stepLoading.value = false;
    if (!stepId.value || !snapshot) return;
    const summary = snapshot.modules
      .flatMap((module) => module.steps)
      .find((item) => item.id === stepId.value);
    if (!summary || summary.locked) return;
    stepLoading.value = true;
    try {
      const result = await studentCourseApi.getStep(stepId.value);
      if (version === stepVersion && !disposed) step.value = result;
    } catch (cause) {
      if (version === stepVersion && !disposed) error.value = errorMessage(cause);
    } finally {
      if (version === stepVersion) stepLoading.value = false;
    }
  }

  async function loadCourse(): Promise<void> {
    const version = ++courseVersion;
    titles.value = new Map();
    course.value = null;
    step.value = null;
    error.value = "";
    loading.value = true;
    try {
      const result = await studentCourseApi.getCourse(courseId.value);
      if (version !== courseVersion || disposed) return;
      course.value = result;
      loading.value = false;
      void loadTitles(result, version);
      await loadSelectedStep(result);
    } catch (cause) {
      if (version === courseVersion && !disposed) {
        error.value = errorMessage(cause);
        loading.value = false;
      }
    }
  }

  async function refresh(): Promise<void> {
    try {
      const currentStepId = stepId.value;
      const result = await studentCourseApi.getCourse(courseId.value);
      if (disposed || result.id !== courseId.value) return;
      course.value = result;
      void loadTitles(result, courseVersion);
      if (currentStepId) {
        const refreshed = await studentCourseApi.getStep(currentStepId);
        if (!disposed && stepId.value === currentStepId) step.value = refreshed;
      }
    } catch {
      // Keep current answer visible; explicit navigation/retry will surface an error.
    }
  }

  watch(courseId, loadCourse, { immediate: true });
  watch(stepId, () => {
    error.value = "";
    void loadSelectedStep();
  });

  onBeforeUnmount(() => {
    disposed = true;
    ++courseVersion;
    ++stepVersion;
  });

  return {
    course,
    step,
    titles,
    loading,
    stepLoading,
    error,
    selectedSummary,
    stepNumber,
    loadCourse,
    refresh,
  };
}
