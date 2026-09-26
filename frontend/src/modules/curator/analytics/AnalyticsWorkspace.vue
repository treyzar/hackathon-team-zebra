<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { getApiErrorMessage } from "@/api/errors";
import type { Course, CourseListItem } from "@/modules/student/courses/types";
import { analyticsApi } from "./api";
import AnalyticsModuleMatrix from "./AnalyticsModuleMatrix.vue";
import AnalyticsModuleTable from "./AnalyticsModuleTable.vue";
import AnalyticsStepDetail from "./AnalyticsStepDetail.vue";
import AnalyticsStudentsTable from "./AnalyticsStudentsTable.vue";
import { averageProgress, hardestModule, lagCounts } from "./presentation";
import type { AnalyticsGroup, CourseAnalytics, ModuleAnalytics } from "./types";
import "./analytics.css";

type View = "course" | "students" | "module" | "step";

const courses = ref<CourseListItem[]>([]);
const groups = ref<AnalyticsGroup[]>([]);
const selectedCourseId = ref<number | "">("");
const selectedGroupId = ref<number | "">("");
const course = ref<Course | null>(null);
const analytics = ref<CourseAnalytics | null>(null);
const moduleData = ref<Record<number, ModuleAnalytics>>({});
const view = ref<View>("course");
const moduleId = ref<number | null>(null);
const stepId = ref<number | null>(null);
const loadingFilters = ref(true);
const loadingData = ref(false);
const loadingModule = ref(false);
const filtersError = ref("");
const dataError = ref("");
const moduleError = ref("");
let requestId = 0;
let moduleRequestId = 0;

const ready = computed(() => selectedCourseId.value !== "" && selectedGroupId.value !== "");
const activeModuleStats = computed(
  () => analytics.value?.modules.find((item) => item.module_id === moduleId.value) ?? null,
);
const activeModule = computed(() => (moduleId.value ? moduleData.value[moduleId.value] : null));
const activeStep = computed(
  () => activeModule.value?.steps.find((item) => item.step_id === stepId.value) ?? null,
);
const activeModuleNumber = computed(
  () => (analytics.value?.modules.findIndex((item) => item.module_id === moduleId.value) ?? -1) + 1,
);
const counts = computed(() => lagCounts(analytics.value?.students ?? []));
const average = computed(() => averageProgress(analytics.value?.students ?? []));
const hardest = computed(() => hardestModule(analytics.value?.modules ?? []));
const stepCounts = computed(() =>
  Object.fromEntries(course.value?.modules.map((item) => [item.id, item.steps.length]) ?? []),
);

async function loadFilters(): Promise<void> {
  loadingFilters.value = true;
  filtersError.value = "";
  try {
    [courses.value, groups.value] = await Promise.all([
      analyticsApi.courses(),
      analyticsApi.groups(),
    ]);
  } catch (cause) {
    filtersError.value = getApiErrorMessage(cause);
  } finally {
    loadingFilters.value = false;
  }
}

async function loadSelection(): Promise<void> {
  const currentRequest = ++requestId;
  ++moduleRequestId;
  course.value = null;
  analytics.value = null;
  moduleData.value = {};
  view.value = "course";
  moduleId.value = null;
  stepId.value = null;
  dataError.value = "";
  moduleError.value = "";
  loadingData.value = false;
  loadingModule.value = false;
  if (!ready.value) return;

  loadingData.value = true;
  try {
    const [courseData, analyticsData] = await Promise.all([
      analyticsApi.course(Number(selectedCourseId.value)),
      analyticsApi.courseAnalytics(Number(selectedGroupId.value), Number(selectedCourseId.value)),
    ]);
    if (currentRequest !== requestId) return;
    course.value = courseData;
    analytics.value = analyticsData;
  } catch (cause) {
    if (currentRequest === requestId) dataError.value = getApiErrorMessage(cause);
  } finally {
    if (currentRequest === requestId) loadingData.value = false;
  }
}

watch([selectedCourseId, selectedGroupId], loadSelection);

function showCourse(): void {
  ++moduleRequestId;
  view.value = "course";
  moduleId.value = null;
  stepId.value = null;
  loadingModule.value = false;
}

async function showModule(id: number): Promise<void> {
  const currentModuleRequest = ++moduleRequestId;
  moduleId.value = id;
  stepId.value = null;
  view.value = "module";
  moduleError.value = "";
  if (moduleData.value[id]) return;
  const currentRequest = requestId;
  loadingModule.value = true;
  try {
    const data = await analyticsApi.moduleAnalytics(
      Number(selectedGroupId.value),
      Number(selectedCourseId.value),
      id,
    );
    if (currentRequest === requestId) moduleData.value = { ...moduleData.value, [id]: data };
  } catch (cause) {
    if (currentRequest === requestId && currentModuleRequest === moduleRequestId)
      moduleError.value = getApiErrorMessage(cause);
  } finally {
    if (currentRequest === requestId && currentModuleRequest === moduleRequestId)
      loadingModule.value = false;
  }
}

function showStep(id: number): void {
  stepId.value = id;
  view.value = "step";
}

onMounted(loadFilters);
</script>

<template>
  <section class="analytics-workspace" aria-label="Аналитика групп">
    <div class="analytics-toolbar">
      <label>
        <span class="analytics-visually-hidden">Курс</span>
        <select v-model="selectedCourseId" :disabled="loadingFilters" aria-label="Курс">
          <option value="">Выберите курс</option>
          <option v-for="item in courses" :key="item.id" :value="item.id">{{ item.title }}</option>
        </select>
      </label>
      <label>
        <span class="analytics-visually-hidden">Группа</span>
        <select v-model="selectedGroupId" :disabled="loadingFilters" aria-label="Группа">
          <option value="">Выберите группу</option>
          <option v-for="item in groups" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
      </label>
    </div>

    <p v-if="filtersError" class="analytics-error" role="alert">
      Не удалось загрузить фильтры: {{ filtersError }}
      <button type="button" @click="loadFilters">Повторить</button>
    </p>

    <nav v-if="ready && analytics" class="analytics-breadcrumbs" aria-label="Уровень аналитики">
      <button type="button" @click="showCourse">Курс целиком</button>
      <template v-if="view === 'students'">
        <span aria-hidden="true">›</span><strong>Ученики по модулям</strong>
      </template>
      <template v-if="activeModuleStats">
        <span aria-hidden="true">›</span>
        <button
          v-if="view === 'step'"
          type="button"
          @click="showModule(activeModuleStats.module_id)"
        >
          {{ activeModuleStats.title }}
        </button>
        <strong v-else>{{ activeModuleStats.title }}</strong>
      </template>
      <template v-if="activeStep">
        <span aria-hidden="true">›</span>
        <strong>{{ activeModuleNumber }}.{{ activeStep.position }} {{ activeStep.title }}</strong>
      </template>
    </nav>

    <div v-if="!ready" class="analytics-card analytics-module-card">
      <div class="analytics-card-heading"><h3>Модули курса</h3></div>
      <div class="analytics-empty">Выберите курс и группу, чтобы увидеть модули и аналитику.</div>
    </div>
    <div v-else-if="loadingData" class="analytics-card analytics-state" role="status">
      Загружаем аналитику…
    </div>
    <div v-else-if="dataError" class="analytics-card analytics-state" role="alert">
      {{ dataError }} <button type="button" @click="loadSelection">Повторить</button>
    </div>
    <template v-else-if="analytics">
      <template v-if="view === 'course'">
        <div class="analytics-summary">
          <div class="analytics-card analytics-metric">
            <strong>{{ average === null ? "—" : `${average}%` }}</strong>
            <span>курса пройдено в среднем</span>
          </div>
          <div class="analytics-card analytics-metric">
            <strong>{{ analytics.students_total }}</strong
            ><span>учеников в группе на курсе</span>
          </div>
          <div class="analytics-card analytics-metric analytics-metric--attention">
            <strong>{{ hardest?.title ?? "—" }}</strong>
            <span>самый трудный модуль по первой попытке</span>
          </div>
        </div>
        <div class="analytics-course-layout">
          <div class="analytics-card analytics-module-card">
            <div class="analytics-card-heading">
              <h3>Модули курса</h3>
              <span>нажмите на модуль, чтобы увидеть шаги</span>
            </div>
            <AnalyticsModuleTable
              :modules="analytics.modules"
              :students-total="analytics.students_total"
              :step-counts="stepCounts"
              @select="showModule"
            />
            <div v-if="!analytics.modules.length" class="analytics-empty">
              В курсе пока нет модулей.
            </div>
            <p v-else class="analytics-table-note">
              «С 1-й попытки» — доля оценённых первых решений с максимальным баллом. «Попыток» —
              среднее на задание.
            </p>
          </div>
          <aside class="analytics-card analytics-students-card">
            <h3>Ученики по модулям</h3>
            <p>Кто где находится в курсе и кому нужна помощь.</p>
            <div class="analytics-pills">
              <span class="analytics-pill analytics-pill--orange"
                >Выпадает · {{ counts.falling }}</span
              >
              <span class="analytics-pill analytics-pill--gray"
                >Замедлились · {{ counts.slowed }}</span
              >
              <span class="analytics-pill analytics-pill--green"
                >В графике · {{ counts.onTrack }}</span
              >
            </div>
            <button type="button" class="analytics-primary" @click="view = 'students'">
              Открыть таблицу учеников →
            </button>
          </aside>
        </div>
      </template>

      <AnalyticsStudentsTable
        v-else-if="view === 'students'"
        :data="analytics"
        @select-module="showModule"
      />

      <div
        v-else-if="view === 'module' && loadingModule"
        class="analytics-card analytics-state"
        role="status"
      >
        Загружаем шаги модуля…
      </div>
      <div
        v-else-if="view === 'module' && moduleError"
        class="analytics-card analytics-state"
        role="alert"
      >
        {{ moduleError }}
        <button type="button" @click="moduleId && showModule(moduleId)">Повторить</button>
      </div>
      <AnalyticsModuleMatrix
        v-else-if="view === 'module' && activeModule"
        :data="activeModule"
        :module-number="activeModuleNumber"
        @select-step="showStep"
      />

      <AnalyticsStepDetail
        v-else-if="view === 'step' && activeModule && activeStep"
        :data="activeModule"
        :step="activeStep"
        :module-number="activeModuleNumber"
      />
    </template>
  </section>
</template>
