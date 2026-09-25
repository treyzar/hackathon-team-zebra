import { ref } from "vue";

import { getApiErrorMessage } from "@/api/errors";
import { getCourse, getStep } from "@/modules/student/courses/api";
import { documentTitle, stepDocument, stepLabels } from "@/modules/student/courses/presentation";
import type { StudentStep } from "@/modules/student/courses/types";
import type { StaffQuestion } from "./types";

export function useQuestionSteps() {
  const steps = ref(new Map<number, StudentStep>());
  const numbers = ref(new Map<number, string>());
  const loading = ref(new Set<number>());
  const errors = ref(new Map<number, string>());
  let version = 0;

  function reset(): void {
    ++version;
    steps.value = new Map();
    numbers.value = new Map();
    loading.value = new Set();
    errors.value = new Map();
  }

  async function loadStep(stepId: number): Promise<void> {
    if (steps.value.has(stepId) || loading.value.has(stepId)) return;
    const current = version;
    loading.value = new Set([...loading.value, stepId]);
    const nextErrors = new Map(errors.value);
    nextErrors.delete(stepId);
    errors.value = nextErrors;
    try {
      const step = await getStep(stepId);
      if (current === version) steps.value = new Map(steps.value).set(stepId, step);
    } catch (cause) {
      if (current === version)
        errors.value = new Map(errors.value).set(stepId, getApiErrorMessage(cause));
    } finally {
      if (current === version) {
        const next = new Set(loading.value);
        next.delete(stepId);
        loading.value = next;
      }
    }
  }

  function preload(items: StaffQuestion[], selectedStepId?: number): void {
    const current = version;
    const courseIds = [...new Set(items.map((item) => item.course_id))];
    void Promise.allSettled(
      courseIds.map(async (courseId) => {
        const course = await getCourse(courseId);
        if (current !== version) return;
        const next = new Map(numbers.value);
        course.modules.forEach((module, moduleIndex) =>
          module.steps.forEach((step, stepIndex) =>
            next.set(step.id, `${moduleIndex + 1}.${stepIndex + 1}`),
          ),
        );
        numbers.value = next;
      }),
    );

    const ids = [...new Set(items.map((item) => item.step_id))];
    if (selectedStepId !== undefined) {
      const index = ids.indexOf(selectedStepId);
      if (index !== -1) {
        ids.splice(index, 1);
        ids.unshift(selectedStepId);
      }
    }
    let cursor = 0;
    void Promise.all(
      Array.from({ length: Math.min(4, ids.length) }, async () => {
        while (cursor < ids.length && current === version) {
          const id = ids[cursor++];
          if (id !== undefined) await loadStep(id);
        }
      }),
    );
  }

  function label(question: StaffQuestion): string {
    const number = numbers.value.get(question.step_id);
    const step = steps.value.get(question.step_id);
    const title = step
      ? documentTitle(stepDocument(step.type, step.content), stepLabels[step.type])
      : `задание #${question.step_id}`;
    return `${number ? `Шаг ${number}` : question.module_title} · ${title}`;
  }

  return { steps, loading, errors, reset, loadStep, preload, label };
}
