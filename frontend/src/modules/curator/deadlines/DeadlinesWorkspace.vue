<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { getApiErrorMessage } from "@/api/errors";
import type { CourseListItem } from "@/modules/student/courses/types";
import { deadlineFromInput, deadlineToInput } from "@/modules/shared/deadline";
import { deadlinesApi } from "./api";
import DeadlineCoursePanel from "./DeadlineCoursePanel.vue";
import DeadlineStepTable from "./DeadlineStepTable.vue";
import { groupSteps, ownInput, validDeadlineInput } from "./presentation";
import type { CourseDeadlineState, DeadlineGroup, StepDeadline } from "./types";
import "./deadlines.css";

const courses = ref<CourseListItem[]>([]);
const groups = ref<DeadlineGroup[]>([]);
const selectedCourseId = ref<number | "">("");
const selectedGroupId = ref<number | "">("");
const courseState = ref<CourseDeadlineState | null>(null);
const steps = ref<StepDeadline[]>([]);
const courseDraft = ref<string | null>(null);
const stepDrafts = ref<Record<number, string | null>>({});
const loadingFilters = ref(true);
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
let requestId = 0;

const ready = computed(() => selectedCourseId.value !== "" && selectedGroupId.value !== "");
const selectedGroup = computed(() =>
  groups.value.find((group) => group.id === selectedGroupId.value),
);
const modules = computed(() => groupSteps(steps.value));
const courseChanged = computed(
  () =>
    courseDraft.value !==
    (courseState.value?.own ? deadlineToInput(courseState.value.own.due_at) : null),
);
const changedSteps = computed(() =>
  steps.value.filter((step) => stepDrafts.value[step.step_id] !== ownInput(step)),
);
const hasChanges = computed(() => courseChanged.value || changedSteps.value.length > 0);

async function loadFilters(): Promise<void> {
  loadingFilters.value = true;
  error.value = "";
  try {
    [courses.value, groups.value] = await Promise.all([
      deadlinesApi.courses(),
      deadlinesApi.groups(),
    ]);
    selectedCourseId.value = courses.value[0]?.id ?? "";
    selectedGroupId.value = groups.value[0]?.id ?? "";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loadingFilters.value = false;
  }
}

async function loadSelection(): Promise<void> {
  const currentRequest = ++requestId;
  courseState.value = null;
  steps.value = [];
  courseDraft.value = null;
  stepDrafts.value = {};
  error.value = "";
  success.value = "";
  if (!ready.value) return;
  loading.value = true;
  try {
    const [state, rows] = await Promise.all([
      deadlinesApi.course(Number(selectedGroupId.value), Number(selectedCourseId.value)),
      deadlinesApi.steps(Number(selectedGroupId.value), Number(selectedCourseId.value)),
    ]);
    if (currentRequest !== requestId) return;
    courseState.value = state;
    steps.value = rows;
    courseDraft.value = state.own ? deadlineToInput(state.own.due_at) : null;
    stepDrafts.value = Object.fromEntries(rows.map((step) => [step.step_id, ownInput(step)]));
  } catch (cause) {
    if (currentRequest === requestId) error.value = getApiErrorMessage(cause);
  } finally {
    if (currentRequest === requestId) loading.value = false;
  }
}

function updateCourse(value: string | null): void {
  courseDraft.value = value;
  error.value = "";
  success.value = "";
}

function updateStep(stepId: number, value: string | null): void {
  stepDrafts.value = { ...stepDrafts.value, [stepId]: value };
  error.value = "";
  success.value = "";
}

async function save(): Promise<void> {
  if (!ready.value || !courseState.value || !hasChanges.value || saving.value) return;
  if (
    (courseChanged.value && courseDraft.value !== null && !validDeadlineInput(courseDraft.value)) ||
    changedSteps.value.some((step) => {
      const value = stepDrafts.value[step.step_id];
      return value !== null && (value === undefined || !validDeadlineInput(value));
    })
  ) {
    error.value = "Укажите дату и время для каждого добавленного срока.";
    return;
  }

  saving.value = true;
  error.value = "";
  success.value = "";
  const groupId = Number(selectedGroupId.value);
  const courseId = Number(selectedCourseId.value);
  let savedCount = 0;
  try {
    if (courseChanged.value) {
      if (courseDraft.value === null) {
        await deadlinesApi.removeCourse(groupId, courseId);
        courseState.value.own = null;
      } else {
        courseState.value = await deadlinesApi.setCourse(
          groupId,
          courseId,
          deadlineFromInput(courseDraft.value)!,
        );
      }
      savedCount += 1;
    }
    for (const step of changedSteps.value) {
      const value = stepDrafts.value[step.step_id];
      if (value === null) {
        await deadlinesApi.removeStep(groupId, step.step_id);
        step.own = null;
      } else if (value !== undefined) {
        step.own = await deadlinesApi.setStep(groupId, step.step_id, deadlineFromInput(value)!);
      }
      savedCount += 1;
    }
    await loadSelection();
    success.value = "Дедлайны сохранены";
  } catch (cause) {
    error.value = savedCount
      ? `Часть сроков сохранена. Повторите сохранение остальных: ${getApiErrorMessage(cause)}`
      : getApiErrorMessage(cause);
  } finally {
    saving.value = false;
  }
}

watch([selectedCourseId, selectedGroupId], loadSelection);
onMounted(loadFilters);
</script>

<template>
  <section class="deadlines-workspace" aria-label="Дедлайны группы">
    <header class="deadlines-toolbar">
      <label>
        <span class="deadlines-visually-hidden">Курс</span>
        <select v-model="selectedCourseId" :disabled="loadingFilters || saving" aria-label="Курс">
          <option value="">Выберите курс</option>
          <option v-for="course in courses" :key="course.id" :value="course.id">
            {{ course.title }}
          </option>
        </select>
      </label>
      <label>
        <span class="deadlines-visually-hidden">Группа</span>
        <select v-model="selectedGroupId" :disabled="loadingFilters || saving" aria-label="Группа">
          <option value="">Выберите группу</option>
          <option v-for="group in groups" :key="group.id" :value="group.id">
            {{ group.name }}
          </option>
        </select>
      </label>
      <button
        class="deadlines-save"
        type="button"
        :disabled="!hasChanges || saving || loading || !ready"
        @click="save"
      >
        {{ saving ? "Сохраняем…" : "Сохранить" }}
      </button>
    </header>

    <p v-if="error" class="deadlines-message deadlines-message--error" role="alert">
      {{ error }}
      <button v-if="!courseState && ready" type="button" @click="loadSelection">Повторить</button>
      <button v-else-if="loadingFilters" type="button" @click="loadFilters">Повторить</button>
    </p>
    <p v-if="success" class="deadlines-message deadlines-message--success" role="status">
      {{ success }}
    </p>

    <div v-if="loadingFilters || loading" class="deadlines-card deadlines-empty" role="status">
      Загружаем дедлайны…
    </div>
    <div v-else-if="!ready" class="deadlines-card deadlines-empty">
      Выберите курс и группу, чтобы настроить сроки.
    </div>
    <div v-else-if="courseState && selectedGroup" class="deadlines-content">
      <DeadlineStepTable
        :group-name="selectedGroup.name"
        :modules="modules"
        :drafts="stepDrafts"
        :disabled="saving"
        @update="updateStep"
      />
      <DeadlineCoursePanel
        :state="courseState"
        :draft="courseDraft"
        :disabled="saving"
        @update="updateCourse"
      />
    </div>
  </section>
</template>
