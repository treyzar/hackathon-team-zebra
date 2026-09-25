<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { getStep, listCourses } from "./api";
import {
  documentTitle,
  errorMessage,
  progressText,
  stepDocument,
  stepLabels,
} from "./presentation";
import type { CourseListItem } from "./types";
import { STUDENT_COURSE_ROUTE } from "@/pages/student/course/constants";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";

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
  points: courses.value.reduce((sum, course) => sum + course.progress.points_earned, 0),
}));

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    courses.value = await listCourses();
    const course = courses.value.find((item) => item.progress.next_step_id != null);
    if (course?.progress.next_step_id != null) {
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
                  : "Здесь появятся опубликованные для вас курсы."
              }}
            </p>
          </template>
        </section>
        <section class="student-snapshot" aria-label="Ваш прогресс">
          <h2>Ваш прогресс</h2>
          <div class="student-snapshot-row">
            <span>Курсов</span><strong>{{ courses.length }}</strong>
          </div>
          <div class="student-snapshot-row">
            <span>Шагов пройдено</span><strong>{{ totals.steps }}</strong>
          </div>
          <div class="student-snapshot-row">
            <span>Баллов набрано</span><strong>{{ totals.points }}</strong>
          </div>
        </section>
      </div>
      <section aria-labelledby="student-courses-heading">
        <div class="student-section-heading">
          <h2 id="student-courses-heading">Мои курсы</h2>
          <span>{{ courses.length }}</span>
        </div>
        <div v-if="!courses.length" class="student-empty">Опубликованных курсов пока нет.</div>
        <div v-else class="student-course-grid">
          <RouterLink
            v-for="(course, index) in courses"
            :key="course.id"
            class="student-course-card"
            :to="{ name: STUDENT_COURSE_ROUTE.name, params: { courseId: course.id } }"
          >
            <span
              class="student-course-mark"
              :class="`student-course-mark--${index % 3}`"
              aria-hidden="true"
              >{{ String(index + 1).padStart(2, "0") }}</span
            >
            <span class="student-course-kicker"
              >КУРС · {{ course.progress.steps_total }} ШАГОВ</span
            >
            <strong>{{ course.title }}</strong>
            <span class="student-progress-track"
              ><span :style="{ width: `${course.progress.percent}%` }"
            /></span>
            <span class="student-course-bottom"
              >{{ progressText(course.progress.steps_completed, course.progress.steps_total) }}
              <span aria-hidden="true">↗</span></span
            >
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
  gap: 29px;
  max-width: 1450px;
  margin: 0 auto;
}
.student-catalog-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 24px;
}
.student-hero {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-height: 292px;
  padding: 32px;
  border-radius: 16px;
  background: radial-gradient(120% 140% at 100% 0%, #1e2f66 0%, #0b1220 60%);
  color: #fff;
}
.student-hero-kicker {
  margin: 0 0 9px;
  color: #9db1ff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.student-hero h2 {
  max-width: 690px;
  margin: 0 0 9px;
  font-size: clamp(26px, 3vw, 36px);
  font-weight: 800;
  line-height: 1.12;
}
.student-hero p:not(.student-hero-kicker) {
  margin: 0 0 20px;
  color: #c9d5fc;
  font-size: 15px;
}
.student-progress-track {
  display: block;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #e1e6f0;
}
.student-progress-track > span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #3457f0;
}
.student-progress-track--dark {
  width: 100%;
  max-width: 650px;
  margin: auto 0 18px;
  background: #26334d;
}
.student-progress-track--dark > span {
  background: #7c95ff;
}
.student-primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  min-height: 52px;
  padding: 0 28px;
  border-radius: 13px;
  background: #3457f0;
  color: white;
  font-size: 16px;
  font-weight: 700;
  text-decoration: none;
}
.student-primary-button:hover {
  background: #2446d4;
}
.student-snapshot {
  display: flex;
  flex-direction: column;
  min-height: 292px;
  padding: 24px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.student-snapshot h2 {
  margin: 0 0 17px;
  font-size: 18px;
}
.student-snapshot-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid #edf0f6;
  color: #59647a;
  font-size: 15px;
}
.student-snapshot-row strong {
  color: #0f172a;
  font-size: 23px;
}
.student-section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 20px;
}
.student-section-heading h2 {
  margin: 0;
  color: #0f172a;
  font-size: 24px;
}
.student-section-heading > span {
  color: #68748a;
  font-size: 15px;
}
.student-course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}
.student-course-card {
  display: flex;
  flex-direction: column;
  min-height: 230px;
  padding: 24px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
  color: #0f172a;
  text-decoration: none;
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}
.student-course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px #14274b12;
}
.student-course-card:focus-visible {
  outline: 3px solid #3457f0;
  outline-offset: 2px;
}
.student-course-mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  margin-bottom: 16px;
  border-radius: 10px;
  background: #eaf0fe;
  color: #3457f0;
  font-size: 13px;
  font-weight: 800;
}
.student-course-mark--1 {
  background: #e4f5ec;
  color: #17915a;
}
.student-course-mark--2 {
  background: #efebfe;
  color: #6e4fe8;
}
.student-course-kicker {
  color: #67728a;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.07em;
}
.student-course-card strong {
  margin: 6px 0 20px;
  font-size: 20px;
  line-height: 1.25;
}
.student-course-card .student-progress-track {
  width: 100%;
  margin-top: auto;
}
.student-course-bottom {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  color: #59647a;
  font-size: 14px;
}
.student-course-bottom span {
  color: #3457f0;
  font-size: 21px;
  line-height: 1;
}
.student-empty {
  padding: 34px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
  color: #65728a;
}
.student-empty--error {
  color: #a83a3a;
}
.student-empty button {
  margin-left: 8px;
  color: #3457f0;
  font-weight: 700;
}
@media (max-width: 1100px) {
  .student-catalog-top {
    grid-template-columns: 1fr;
  }
  .student-snapshot {
    min-height: auto;
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
    padding: 25px;
    min-height: 280px;
  }
}
</style>
