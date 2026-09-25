<script setup lang="ts">
import { RouterLink } from "vue-router";
import type { CourseListItem } from "../types";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";

defineProps<{
  course: CourseListItem | undefined;
  nextTitle: string;
  nextType: string;
  hasCourses: boolean;
}>();
</script>

<template>
  <section class="student-hero">
    <template v-if="course?.progress.next_step_id != null">
      <p class="student-hero-kicker">
        СЛЕДУЮЩИЙ ШАГ · {{ course.progress.steps_completed + 1 }} ИЗ
        {{ course.progress.steps_total }}
      </p>
      <h2>{{ nextTitle || "Следующий шаг" }}</h2>
      <p>{{ nextType || "Задание" }} · курс «{{ course.title }}»</p>
      <div class="student-progress-track student-progress-track--dark">
        <span :style="{ width: `${course.progress.percent}%` }" />
      </div>
      <RouterLink
        class="student-primary-button"
        :to="{
          name: STUDENT_STEP_ROUTE.name,
          params: { courseId: course.id, stepId: course.progress.next_step_id },
        }"
        >Продолжить <span aria-hidden="true">→</span></RouterLink
      >
    </template>
    <template v-else>
      <p class="student-hero-kicker">МОИ КУРСЫ</p>
      <h2>{{ hasCourses ? "Отличная работа!" : "Пора начать обучение" }}</h2>
      <p>
        {{
          hasCourses
            ? "Все доступные шаги пройдены. Загляните в свои курсы."
            : "Здесь появятся опубликованные для вас курсы."
        }}
      </p>
    </template>
  </section>
</template>

<style scoped>
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
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  text-decoration: none;
}
.student-primary-button:hover {
  background: #2446d4;
}
</style>
