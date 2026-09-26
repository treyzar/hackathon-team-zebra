<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { getCourse, getStep } from "./api";
import {
  documentTitle,
  errorMessage,
  pointsText,
  progressText,
  stepDocument,
  stepLabels,
} from "./presentation";
import RichContent from "./RichContent.vue";
import type { Course, StudentStep } from "./types";
import StepPlayer from "@/modules/student/steps/StepPlayer.vue";
import { STUDENT_COURSES_ROUTE } from "@/pages/student/courses/constants";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";
import StepComments from "@/modules/student/steps/StepComments.vue";

const props = defineProps<{ courseId: number; stepId?: number }>();
const course = ref<Course | null>(null);
const step = ref<StudentStep | null>(null);
const titles = ref(new Map<number, string>());
const loading = ref(true);
const stepLoading = ref(false);
const error = ref("");
const outlineOpen = ref(false);
const mobile = ref(false);
const outlineButton = ref<HTMLButtonElement | null>(null);
const outlineCloseButton = ref<HTMLButtonElement | null>(null);
const workspaceMain = ref<HTMLElement | null>(null);
const outlineHidden = computed(() => mobile.value && !outlineOpen.value);
let courseVersion = 0;
let stepVersion = 0;
let disposed = false;
let mobileQuery: MediaQueryList | null = null;

function updateMobile(event: MediaQueryListEvent): void {
  mobile.value = event.matches;
  if (!event.matches) outlineOpen.value = false;
}

function closeOutline(): void {
  outlineOpen.value = false;
  if (mobile.value) void nextTick(() => outlineButton.value?.focus());
}

onMounted(() => {
  mobileQuery = window.matchMedia("(max-width: 767px)");
  mobile.value = mobileQuery.matches;
  mobileQuery.addEventListener("change", updateMobile);
});

const selected = computed(() =>
  course.value?.modules.flatMap((module) => module.steps).find((item) => item.id === props.stepId),
);
// The next step in course order, offered once the current one is done.
const nextStep = computed(() => {
  const steps = course.value?.modules.flatMap((module) => module.steps) ?? [];
  const index = steps.findIndex((item) => item.id === props.stepId);
  const next = index === -1 ? undefined : steps[index + 1];
  return course.value && next && !next.locked
    ? { name: STUDENT_STEP_ROUTE.name, params: { courseId: course.value.id, stepId: next.id } }
    : null;
});
const stepNumber = computed(() => {
  if (!course.value || !props.stepId) return "";
  for (const [moduleIndex, module] of course.value.modules.entries()) {
    const stepIndex = module.steps.findIndex((item) => item.id === props.stepId);
    if (stepIndex !== -1) return `${moduleIndex + 1}.${stepIndex + 1}`;
  }
  return "";
});

async function loadTitles(snapshot: Course, version: number): Promise<void> {
  const waiting = snapshot.modules
    .flatMap((module) => module.steps)
    .filter((item) => !item.locked && !titles.value.has(item.id));
  // The course summary has no step title; fetch only open steps, with a small concurrency limit.
  let cursor = 0;
  await Promise.all(
    Array.from({ length: Math.min(6, waiting.length) }, async () => {
      while (cursor < waiting.length && version === courseVersion && !disposed) {
        const item = waiting[cursor++];
        if (!item) continue;
        try {
          const detail = await getStep(item.id);
          if (version !== courseVersion || disposed) return;
          const next = new Map(titles.value);
          next.set(
            item.id,
            documentTitle(stepDocument(detail.type, detail.content), stepLabels[detail.type]),
          );
          titles.value = next;
        } catch {
          // A step may become locked or unpublished during refresh.
        }
      }
    }),
  );
}

async function loadSelectedStep(snapshot = course.value): Promise<void> {
  const version = ++stepVersion;
  step.value = null;
  stepLoading.value = false;
  if (!props.stepId || !snapshot) return;
  const summary = snapshot.modules
    .flatMap((module) => module.steps)
    .find((item) => item.id === props.stepId);
  if (!summary || summary.locked) return;
  stepLoading.value = true;
  try {
    const result = await getStep(props.stepId);
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
    const result = await getCourse(props.courseId);
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
    const stepId = props.stepId;
    const result = await getCourse(props.courseId);
    if (disposed || result.id !== props.courseId) return;
    course.value = result;
    void loadTitles(result, courseVersion);
    if (stepId) {
      const refreshed = await getStep(stepId);
      if (!disposed && props.stepId === stepId) step.value = refreshed;
    }
  } catch {
    // The current answer remains visible; the next navigation will reload progress.
  }
}

watch(
  () => props.courseId,
  () => {
    outlineOpen.value = false;
    if (workspaceMain.value) workspaceMain.value.scrollTop = 0;
    void loadCourse();
  },
  { immediate: true },
);
watch(
  () => props.stepId,
  () => {
    outlineOpen.value = false;
    if (workspaceMain.value) workspaceMain.value.scrollTop = 0;
    error.value = "";
    void loadSelectedStep();
  },
);
watch(outlineOpen, async (open) => {
  if (open) {
    await nextTick();
    outlineCloseButton.value?.focus();
  }
});
onBeforeUnmount(() => {
  disposed = true;
  ++courseVersion;
  ++stepVersion;
  mobileQuery?.removeEventListener("change", updateMobile);
});
</script>

<template>
  <div class="student-workspace">
    <div v-if="loading" class="student-workspace-loading" role="status">Загружаем курс…</div>
    <div v-else-if="!course" class="student-workspace-loading student-workspace-error" role="alert">
      {{ error }} <button type="button" @click="loadCourse">Повторить</button>
    </div>
    <template v-else>
      <div class="student-mobile-toolbar">
        <div>
          <RouterLink :to="{ name: STUDENT_COURSES_ROUTE.name }" class="student-back-link"
            >← Мои курсы</RouterLink
          >
          <strong>{{ course.title }}</strong>
        </div>
        <button
          ref="outlineButton"
          type="button"
          aria-controls="student-course-outline"
          :aria-expanded="outlineOpen"
          @click="outlineOpen = true"
        >
          Шаги курса
        </button>
      </div>
      <button
        v-if="outlineOpen && mobile"
        class="student-outline-backdrop"
        type="button"
        aria-label="Закрыть оглавление курса"
        tabindex="-1"
        @click="closeOutline"
      />
      <aside
        id="student-course-outline"
        class="student-outline"
        :class="{ 'student-outline--open': outlineOpen }"
        :aria-hidden="outlineHidden ? 'true' : undefined"
        :inert="outlineHidden"
        aria-label="Модули и шаги курса"
        @keydown.esc="closeOutline"
      >
        <div class="student-outline-head">
          <button
            ref="outlineCloseButton"
            class="student-outline-close"
            type="button"
            aria-label="Закрыть оглавление курса"
            @click="closeOutline"
          >
            ✕
          </button>
          <RouterLink :to="{ name: STUDENT_COURSES_ROUTE.name }" class="student-back-link"
            >← Мои курсы</RouterLink
          >
          <h2>{{ course.title }}</h2>
          <div class="student-outline-totals">
            <span>{{
              progressText(course.progress.steps_completed, course.progress.steps_total)
            }}</span>
            <strong
              >{{ course.progress.points_earned }} из
              {{ course.progress.points_max }} баллов</strong
            >
          </div>
          <div class="student-outline-progress">
            <span :style="{ width: `${course.progress.percent}%` }" />
          </div>
        </div>
        <nav class="student-outline-scroll">
          <section
            v-for="(module, moduleIndex) in course.modules"
            :key="module.id"
            class="student-outline-module"
          >
            <h3>{{ moduleIndex + 1 }}. {{ module.title }}</h3>
            <div v-for="(item, stepIndex) in module.steps" :key="item.id">
              <span
                v-if="item.locked"
                class="student-outline-step student-outline-step--locked"
                title="Шаг ещё закрыт"
              >
                <span class="student-step-icon student-step-icon--locked" aria-hidden="true"
                  >○</span
                >
                <span
                  >{{ stepLabels[item.type] }}
                  <small>{{ moduleIndex + 1 }}.{{ stepIndex + 1 }}</small>
                  <small v-if="item.deadline" class="student-step-deadline"
                    >До {{ new Date(item.deadline.due_at).toLocaleDateString("ru-RU") }}</small
                  ></span
                >
                <small class="student-step-score">{{ item.max_score }}</small>
              </span>
              <RouterLink
                v-else
                class="student-outline-step"
                :class="{ 'student-outline-step--active': item.id === stepId }"
                :to="{
                  name: STUDENT_STEP_ROUTE.name,
                  params: { courseId: course.id, stepId: item.id },
                }"
                @click="closeOutline"
              >
                <span
                  class="student-step-icon"
                  :class="`student-step-icon--${item.progress.state}`"
                  aria-hidden="true"
                >
                  {{
                    item.progress.state === "passed"
                      ? "✓"
                      : item.progress.state === "checking"
                        ? "◷"
                        : item.progress.state === "failed" ||
                            item.progress.state === "attempts_exhausted"
                          ? "↺"
                          : item.id === stepId
                            ? "●"
                            : "○"
                  }}
                </span>
                <span
                  >{{ titles.get(item.id) || stepLabels[item.type] }}
                  <small>{{ moduleIndex + 1 }}.{{ stepIndex + 1 }}</small>
                  <small v-if="item.deadline" class="student-step-deadline"
                    >До {{ new Date(item.deadline.due_at).toLocaleDateString("ru-RU") }}</small
                  ></span
                >
                <small
                  v-if="item.max_score"
                  class="student-step-score"
                  :class="{ 'student-step-score--earned': item.progress.earned > 0 }"
                  >{{
                    item.progress.earned > 0 ? `+${item.progress.earned}` : item.max_score
                  }}</small
                >
              </RouterLink>
            </div>
          </section>
          <p v-if="!course.modules.length" class="student-outline-empty">
            Модули пока не опубликованы.
          </p>
        </nav>
      </aside>
      <section
        ref="workspaceMain"
        class="student-workspace-main"
        :inert="mobile && outlineOpen"
        aria-label="Материал курса"
      >
        <div v-if="error" class="student-workspace-error" role="alert">{{ error }}</div>
        <template v-if="stepId">
          <div v-if="selected?.locked" class="student-step-unavailable">
            <h2>Шаг пока закрыт</h2>
            <p>Завершите предыдущие шаги курса, чтобы открыть этот.</p>
          </div>
          <div v-else-if="stepLoading" class="student-workspace-loading" role="status">
            Загружаем шаг…
          </div>
          <template v-else-if="step">
            <StepPlayer
              :key="step.id"
              :step="step"
              :number="stepNumber"
              :next="nextStep"
              @refresh="refresh"
            />
            <StepComments :key="`comments-${step.id}`" :step-id="step.id" />
          </template>
          <div v-else class="student-step-unavailable">
            <h2>Шаг не найден</h2>
            <p>Вернитесь к оглавлению курса.</p>
          </div>
        </template>
        <div v-else class="student-course-overview">
          <p class="student-overview-kicker">МОЙ КУРС · {{ course.progress.percent }}% ПРОЙДЕНО</p>
          <h2>{{ course.title }}</h2>
          <div class="student-overview-stat">
            {{ progressText(course.progress.steps_completed, course.progress.steps_total) }} ·
            {{ course.progress.points_earned }} из {{ pointsText(course.progress.points_max) }}
          </div>
          <div class="student-overview-progress">
            <span :style="{ width: `${course.progress.percent}%` }" />
          </div>
          <RichContent :document="course.description" class="student-course-description" />
          <RouterLink
            v-if="course.progress.next_step_id != null"
            class="student-overview-button"
            :to="{
              name: STUDENT_STEP_ROUTE.name,
              params: { courseId: course.id, stepId: course.progress.next_step_id },
            }"
            >{{ course.progress.steps_completed ? "Продолжить обучение" : "Начать обучение" }}
            <span aria-hidden="true">→</span></RouterLink
          >
          <p v-else-if="course.progress.steps_total" class="student-course-complete">
            Все доступные шаги выполнены.
          </p>
          <h3>Модули курса</h3>
          <div class="student-module-list">
            <section
              v-for="(module, index) in course.modules"
              :key="module.id"
              class="student-module-card"
            >
              <span class="student-module-number">{{ String(index + 1).padStart(2, "0") }}</span>
              <div>
                <h4>{{ module.title }}</h4>
                <p>
                  {{ progressText(module.progress.steps_completed, module.progress.steps_total) }}
                </p>
              </div>
              <strong>{{ module.progress.percent }}%</strong>
            </section>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.student-workspace {
  display: grid;
  grid-template-columns: 310px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  min-height: 0;
  color: var(--color-text);
  background: var(--color-bg);
}
.student-mobile-toolbar,
.student-outline-backdrop,
.student-outline-close {
  display: none;
}
.student-outline {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-right: 1px solid #e1e6f0;
}
.student-outline-head {
  flex: none;
  padding: 24px 20px 16px;
  border-bottom: 1px solid var(--color-border);
}
.student-back-link {
  color: var(--color-primary);
  font-size: 15px;
  text-decoration: none;
}
.student-outline-head h2 {
  margin: 8px 0 4px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.student-outline-totals {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin: 0 0 12px;
  color: var(--color-muted);
  font-size: 15px;
}
.student-outline-totals strong {
  color: var(--color-text);
  font-size: var(--font-size-small);
  white-space: nowrap;
}
.student-outline-progress,
.student-overview-progress {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-border);
}
.student-outline-progress span,
.student-overview-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
}
.student-outline-scroll {
  min-height: 0;
  overflow-y: auto;
  padding: 4px 20px 28px;
}
.student-outline-module h3 {
  margin: 16px 0 6px;
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  line-height: 1.4;
  text-transform: uppercase;
  overflow-wrap: anywhere;
}
.student-outline-module > div + div {
  margin-top: 8px;
}
.student-outline-step {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: var(--button-height);
  padding: 8px 10px;
  border-radius: var(--radius-control);
  color: var(--color-text);
  font-size: var(--font-size-base);
  line-height: 1.3;
  text-decoration: none;
}
.student-outline-step small {
  display: block;
  color: var(--color-subtle);
  font-size: var(--font-size-small);
}
.student-outline-step .student-step-score {
  flex: none;
  margin-left: auto;
  font-size: var(--font-size-small);
  font-weight: 600;
}
.student-outline-step .student-step-score--earned {
  color: var(--color-success);
}
.student-outline-step > span:nth-child(2) {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
.student-outline-step .student-step-deadline {
  color: var(--color-warning);
}
.student-outline-step:hover:not(.student-outline-step--locked) {
  background: var(--color-bg);
  color: var(--color-text);
}
.student-outline-step--active,
.student-outline-step--active:hover:not(.student-outline-step--locked) {
  background: var(--color-primary-soft);
  box-shadow: 0 0 0 3px var(--color-primary-pale);
  font-weight: 700;
}
.student-outline-step--locked {
  color: #8a93a8;
  cursor: not-allowed;
}
.student-step-icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 26px;
  height: 26px;
  border: 2px solid #8a93a8;
  border-radius: 50%;
  color: #5e677d;
  font-size: var(--font-size-small);
}
.student-step-icon--passed {
  border: 0;
  background: #e4f5ec;
  color: #17915a;
  font-weight: 800;
}
.student-step-icon--checking {
  border: 0;
  background: #efebfe;
  color: #6e4fe8;
}
.student-step-icon--failed,
.student-step-icon--attempts_exhausted,
.student-step-icon--partial {
  border: 0;
  background: #fff1e6;
  color: #b8520f;
}
.student-outline-step--active .student-step-icon:not(.student-step-icon--passed) {
  border: 0;
  background: #3457f0;
  color: #fff;
}
.student-outline-empty {
  margin: 16px 8px;
  color: #7b8497;
  font-size: var(--font-size-small);
}
.student-workspace-main {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 28px clamp(24px, 3vw, 36px) 64px;
}
.student-workspace-loading,
.student-step-unavailable {
  padding: 35px;
  color: #65728a;
}
.student-workspace > .student-workspace-loading {
  grid-column: 1 / -1;
}
.student-workspace-error {
  margin: 0 0 20px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #fcebeb;
  color: #a53b3b;
}
.student-workspace-error button {
  min-height: var(--button-height);
  border: 0;
  background: transparent;
  color: #3457f0;
  font: inherit;
  font-weight: 700;
}
.student-course-overview {
  max-width: 890px;
}
.student-overview-kicker {
  margin: 0 0 12px;
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.student-course-overview h2 {
  margin: 0 0 12px;
  font-size: clamp(28px, 3vw, 36px);
  font-weight: 800;
  line-height: 1.1;
}
.student-overview-stat {
  color: #5d687d;
  font-size: 15px;
}
.student-overview-progress {
  margin: 17px 0 24px;
}
.student-course-description {
  margin-bottom: 24px;
  padding: 24px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.student-overview-button {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  min-height: var(--button-height);
  padding: 0 32px;
  border-radius: var(--button-radius);
  background: var(--color-primary);
  color: #fff;
  font-size: var(--font-size-base);
  font-weight: 700;
  text-decoration: none;
}
.student-overview-button:hover {
  background: var(--color-primary-hover);
  color: #fff;
}
.student-course-complete {
  display: inline-block;
  padding: 13px 18px;
  border-radius: 10px;
  background: #e4f5ec;
  color: #17915a;
  font-weight: 700;
}
.student-course-overview h3 {
  margin: 32px 0 16px;
  font-size: 24px;
  font-weight: 700;
}
.student-module-list {
  display: grid;
  gap: 12px;
}
.student-module-card {
  display: flex;
  align-items: center;
  gap: 17px;
  min-height: 84px;
  padding: 16px 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #fff;
}
.student-module-number {
  color: #3457f0;
  font-size: 24px;
  font-weight: 800;
}
.student-module-card h4 {
  margin: 0 0 4px;
  font-size: var(--font-size-base);
}
.student-module-card p {
  margin: 0;
  color: #65728a;
  font-size: var(--font-size-small);
}
.student-module-card strong {
  margin-left: auto;
  color: #3457f0;
}
@media (max-width: 900px) {
  .student-workspace {
    grid-template-columns: 245px minmax(0, 1fr);
  }
}
@media (max-width: 767px) {
  .student-workspace {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
  }
  .student-mobile-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
    padding: 12px 16px;
    border-bottom: 1px solid var(--color-border);
    background: #fff;
  }
  .student-mobile-toolbar > div {
    display: grid;
    gap: 2px;
    min-width: 0;
  }
  .student-mobile-toolbar strong {
    overflow: hidden;
    font-size: 15px;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .student-mobile-toolbar button {
    flex: none;
    min-height: var(--button-height);
    padding: 0 12px;
    border: 1px solid var(--color-primary-pale);
    border-radius: 10px;
    background: var(--color-primary-soft);
    color: var(--color-primary);
    font: 700 var(--font-size-small) var(--font-sans);
    cursor: pointer;
  }
  .student-outline-backdrop {
    position: fixed;
    z-index: 20;
    inset: 0;
    display: block;
    width: 100%;
    border: 0;
    background: #0b122080;
  }
  .student-outline {
    position: fixed;
    z-index: 21;
    inset: 0 auto 0 0;
    width: min(360px, calc(100vw - 24px));
    height: 100dvh;
    visibility: hidden;
    transform: translateX(-100%);
    transition:
      transform 0.2s ease,
      visibility 0.2s;
    box-shadow: 12px 0 30px #0b12202e;
    pointer-events: none;
  }
  .student-outline--open {
    visibility: visible;
    transform: translateX(0);
    pointer-events: auto;
  }
  .student-outline-close {
    display: grid;
    float: right;
    width: var(--button-height);
    height: var(--button-height);
    place-items: center;
    margin: -8px -8px 0 8px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: var(--color-muted);
    font-size: 18px;
    cursor: pointer;
  }
  .student-outline-head {
    padding: 20px 17px 14px;
  }
  .student-outline-scroll {
    padding: 4px 17px 28px;
  }
  .student-workspace-main {
    padding: 22px 16px 48px;
    overflow-x: hidden;
  }
  .student-course-overview h2 {
    overflow-wrap: anywhere;
    font-size: 28px;
  }
  .student-course-description {
    padding: 18px;
  }
  .student-overview-button {
    justify-content: center;
    width: 100%;
    padding: 0 16px;
    font-size: 16px;
  }
  .student-module-card {
    gap: 12px;
    min-width: 0;
    padding: 14px;
  }
  .student-module-card > div {
    min-width: 0;
    overflow-wrap: anywhere;
  }
}
@media (prefers-reduced-motion: reduce) {
  .student-outline {
    transition: none;
  }
}
</style>
