<script setup lang="ts">
import { RouterLink } from "vue-router";
import RichContent from "../RichContent.vue";
import { progressText } from "../presentation";
import type { Course } from "../types";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";

defineProps<{ course: Course }>();
</script>

<template>
  <div class="student-course-overview">
    <p class="student-overview-kicker">МОЙ КУРС · {{ course.progress.percent }}% ПРОЙДЕНО</p>
    <h2>{{ course.title }}</h2>
    <div class="student-overview-stat">
      {{ progressText(course.progress.steps_completed, course.progress.steps_total) }} ·
      {{ course.progress.points_earned }} из {{ course.progress.points_max }} баллов
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
          <p>{{ progressText(module.progress.steps_completed, module.progress.steps_total) }}</p>
        </div>
        <strong>{{ module.progress.percent }}%</strong>
      </section>
    </div>
  </div>
</template>

<style scoped>
.student-course-overview {
  max-width: 890px;
}
.student-overview-kicker {
  margin: 0 0 11px;
  color: #3457f0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.student-course-overview h2 {
  margin: 0 0 12px;
  font-size: clamp(29px, 3vw, 39px);
  font-weight: 800;
  line-height: 1.13;
}
.student-overview-stat {
  color: #5d687d;
  font-size: 15px;
}
.student-overview-progress {
  height: 7px;
  overflow: hidden;
  margin: 17px 0 24px;
  border-radius: 999px;
  background: #e1e6f0;
}
.student-overview-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #3457f0;
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
  padding: 0 26px;
  border-radius: var(--button-radius);
  background: #3457f0;
  color: #fff;
  font-size: var(--font-size-base);
  font-weight: 700;
  text-decoration: none;
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
  margin: 35px 0 16px;
  font-size: 23px;
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
  border: 1px solid #e1e6f0;
  border-radius: 15px;
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
</style>
