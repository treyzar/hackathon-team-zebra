<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { getStep, listCourses } from "./api";
import { useAuthStore } from "@/stores/auth";
import { studentCourseApi } from "./api";
import { documentTitle, errorMessage, stepDocument, stepLabels } from "./presentation";
import type { CourseListItem, StudentNotification } from "./types";
import CatalogHero from "./components/CatalogHero.vue";
import CatalogSnapshot from "./components/CatalogSnapshot.vue";
import CourseCatalogCard from "./components/CourseCatalogCard.vue";

withDefaults(
  defineProps<{
    /** Home page mode: the next step and points above the course list. */
    overview?: boolean;
  }>(),
  { overview: false },
);

const auth = useAuthStore();
const courses = ref<CourseListItem[]>([]);
const notifications = ref<StudentNotification[]>([]);
const loading = ref(true);
const error = ref("");
const nextTitle = ref("");
const nextType = ref("");
const nextCourse = computed(() =>
  courses.value.find((course) => course.progress.next_step_id != null),
);
const totals = computed(() => ({
  steps: courses.value.reduce((sum, course) => sum + course.progress.steps_completed, 0),
  stepsTotal: courses.value.reduce((sum, course) => sum + course.progress.steps_total, 0),
  points: courses.value.reduce((sum, course) => sum + course.progress.points_earned, 0),
  pointsMax: courses.value.reduce((sum, course) => sum + course.progress.points_max, 0),
}));

async function loadNextStepTitle(course: CourseListItem | undefined): Promise<void> {
  nextTitle.value = "";
  nextType.value = "";
  if (course?.progress.next_step_id == null) return;
  try {
    const step = await studentCourseApi.getStep(course.progress.next_step_id);
    nextTitle.value = documentTitle(stepDocument(step.type, step.content), stepLabels[step.type]);
    nextType.value = stepLabels[step.type];
  } catch {
    nextTitle.value = "Следующий шаг";
  }
}

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const [courseList, recentNotifications] = await Promise.all([
      studentCourseApi.listCourses(),
      studentCourseApi.listNotifications({ limit: 2 }),
    ]);
    courses.value = courseList;
    notifications.value = recentNotifications;
    await loadNextStepTitle(nextCourse.value);
  } catch (cause) {
    error.value = errorMessage(cause);
  } finally {
    loading.value = false;
  }
}

function percentOf(value: number, total: number): number {
  return total ? Math.round((value / total) * 100) : 0;
}

onMounted(load);
</script>

<template>
  <div class="student-catalog">
    <div v-if="loading" class="student-empty" role="status">Загружаем курсы…</div>
    <div v-else-if="error" class="student-empty student-empty--error" role="alert">
      {{ error }} <button type="button" @click="load">Повторить</button>
    </div>

    <template v-else>
      <div class="student-catalog-top">
        <CatalogHero
          :course="nextCourse"
          :next-title="nextTitle"
          :next-type="nextType"
          :has-courses="Boolean(courses.length)"
        />
        <CatalogSnapshot :courses="courses" :notifications="notifications" />
      </div>

      <section aria-labelledby="student-courses-heading">
        <div class="student-section-heading">
          <h2 id="student-courses-heading">Мои курсы</h2>
        </div>

        <div v-if="!courses.length" class="student-empty">Опубликованных курсов пока нет.</div>
        <div v-else class="student-course-grid">
          <CourseCatalogCard v-for="course in courses" :key="course.id" :course="course" />
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.student-catalog {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1440px;
  margin: 0 auto;
  font-size: 18px;
  line-height: 1.6;
}
.student-catalog-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 24px;
}
.student-catalog-top > :first-child {
  min-width: 0;
  flex: 1;
}
.student-section-heading {
  margin: 2px 0 12px;
}
.student-hero {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 26px 28px;
  border-radius: var(--radius-card);
  background: radial-gradient(120% 140% at 100% 0%, #1e2f66 0%, var(--color-ink) 60%);
  color: #fff;
}
.student-hero-kicker {
  margin: 0;
  color: var(--color-primary-light);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.student-hero h2 {
  max-width: 690px;
  margin: 0;
  font-size: clamp(28px, 3vw, 36px);
  font-weight: 800;
  line-height: 1.1;
}
.student-hero p:not(.student-hero-kicker) {
  margin: 0;
  color: var(--color-primary-pale);
  font-size: 15px;
}
.student-progress-track {
  display: block;
  width: 100%;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-border);
}
.student-progress-track > span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
}
.student-progress-track--dark {
  margin-top: 8px;
  background: #131c30;
}
.student-progress-track--dark > span {
  background: var(--color-primary-light);
}
.student-primary-button {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-height: 56px;
  margin-top: 8px;
  padding: 0 32px;
  border-radius: 14px;
  background: var(--color-primary);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  text-decoration: none;
}
.student-primary-button:hover {
  background: var(--color-primary-hover);
  color: #fff;
}
.student-points {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}
.student-points h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.student-points-value {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0;
  font-size: 22px;
}
.student-section-heading span {
  display: grid;
  min-width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 999px;
  background: #eaf0fe;
  color: #3457f0;
  font-size: 12px;
  font-weight: 800;
}
.student-points-value strong {
  color: var(--color-text);
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
}
.student-points-facts {
  display: grid;
  margin: 4px 0 0;
}
.student-points-facts div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid var(--color-border);
  font-size: 15px;
}
.student-points-facts dt {
  color: var(--color-muted);
}
.student-points-facts dd {
  margin: 0;
  font-weight: 700;
}
.student-section-heading {
  margin: 0 0 16px;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.25;
}
.student-course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}
.student-course-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-text);
  text-decoration: none;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.student-course-card:hover {
  border-color: var(--color-primary-pale);
  box-shadow: 0 12px 32px #14274b12;
  color: var(--color-text);
}
.student-course-meta {
  color: var(--color-muted);
  font-size: 15px;
}
.student-course-card strong {
  font-weight: 700;
  line-height: 1.35;
}
.student-course-card .student-progress-track {
  margin-top: auto;
}
.student-course-bottom {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--color-muted);
  font-size: 15px;
}
.student-course-bottom b {
  color: var(--color-text);
}
.student-empty {
  padding: 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-muted);
  font-size: 16px;
}
.student-empty--error {
  color: var(--color-danger);
}
.student-empty button {
  margin-left: 8px;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
@media (max-width: 1100px) {
  .student-catalog-top {
    grid-template-columns: 1fr;
  }
  .student-course-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 680px) {
  .student-course-grid {
    grid-template-columns: 1fr;
  }
  .student-hero {
    padding: 24px;
  }
}
</style>
