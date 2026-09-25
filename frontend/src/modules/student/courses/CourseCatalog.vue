<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { getStep, listCourses } from "./api";
import {
  documentTitle,
  errorMessage,
  pointsText,
  progressText,
  stepDocument,
  stepLabels,
} from "./presentation";
import type { CourseListItem } from "./types";
import { STUDENT_COURSE_ROUTE } from "@/pages/student/course/constants";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";

const props = withDefaults(
  defineProps<{
    /** Home page mode: the next step and points above the course list. */
    overview?: boolean;
  }>(),
  { overview: false },
);

const courses = ref<CourseListItem[]>([]);
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

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    courses.value = await listCourses();
    const course = courses.value.find((item) => item.progress.next_step_id != null);
    if (props.overview && course?.progress.next_step_id != null) {
      try {
        const step = await getStep(course.progress.next_step_id);
        nextTitle.value = documentTitle(
          stepDocument(step.type, step.content),
          stepLabels[step.type],
        );
        nextType.value = stepLabels[step.type];
      } catch {
        nextTitle.value = "Следующий шаг";
      }
    }
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
      <div v-if="overview" class="student-catalog-top">
        <section class="student-hero">
          <template v-if="nextCourse?.progress.next_step_id != null">
            <p class="student-hero-kicker">
              СЛЕДУЮЩИЙ ШАГ · {{ nextCourse.progress.steps_completed + 1 }} ИЗ
              {{ nextCourse.progress.steps_total }}
            </p>
            <h2>{{ nextTitle || "Следующий шаг" }}</h2>
            <p>{{ nextType || "Задание" }} · курс «{{ nextCourse.title }}»</p>
            <div class="student-progress-track student-progress-track--dark">
              <span :style="{ width: `${nextCourse.progress.percent}%` }" />
            </div>
            <RouterLink
              class="student-primary-button"
              :to="{
                name: STUDENT_STEP_ROUTE.name,
                params: { courseId: nextCourse.id, stepId: nextCourse.progress.next_step_id },
              }"
              >Продолжить <span aria-hidden="true">→</span></RouterLink
            >
          </template>
          <template v-else>
            <p class="student-hero-kicker">МОИ КУРСЫ</p>
            <h2>{{ courses.length ? "Отличная работа!" : "Пора начать обучение" }}</h2>
            <p>
              {{
                courses.length
                  ? "Все доступные шаги пройдены. Загляните в свои курсы."
                  : "Здесь появятся курсы, на которые вас записали."
              }}
            </p>
          </template>
        </section>
        <section class="student-points" aria-labelledby="student-points-heading">
          <h2 id="student-points-heading">Мои баллы</h2>
          <p class="student-points-value">
            <strong>{{ totals.points }}</strong>
            <span v-if="totals.pointsMax">из {{ totals.pointsMax }}</span>
          </p>
          <span class="student-progress-track"
            ><span :style="{ width: `${percentOf(totals.points, totals.pointsMax)}%` }"
          /></span>
          <dl class="student-points-facts">
            <div>
              <dt>Курсов</dt>
              <dd>{{ courses.length }}</dd>
            </div>
            <div>
              <dt>Шагов пройдено</dt>
              <dd>{{ totals.steps }} из {{ totals.stepsTotal }}</dd>
            </div>
          </dl>
        </section>
      </div>
      <section aria-labelledby="student-courses-heading">
        <h2 id="student-courses-heading" class="student-section-heading">Мои курсы</h2>
        <div v-if="!courses.length" class="student-empty">
          Вас пока не записали ни на один курс.
        </div>
        <div v-else class="student-course-grid">
          <RouterLink
            v-for="course in courses"
            :key="course.id"
            class="student-course-card"
            :to="{ name: STUDENT_COURSE_ROUTE.name, params: { courseId: course.id } }"
          >
            <span class="student-course-meta">Курс · {{ course.progress.steps_total }} шагов</span>
            <strong>{{ course.title }}</strong>
            <span class="student-progress-track"
              ><span :style="{ width: `${course.progress.percent}%` }"
            /></span>
            <span v-if="course.progress.steps_completed" class="student-course-bottom">
              <span>{{
                progressText(course.progress.steps_completed, course.progress.steps_total)
              }}</span>
              <b>{{ pointsText(course.progress.points_earned) }}</b>
            </span>
            <span v-else class="student-course-bottom">○ Не начато</span>
          </RouterLink>
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
  color: var(--color-muted);
  font-size: 15px;
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
