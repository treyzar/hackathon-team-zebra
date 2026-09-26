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
      <p class="student-hero-description">
        {{ nextType || "Задание" }} · курс «{{ course.title }}»
      </p>

      <div class="student-progress-track student-progress-track--dark" aria-hidden="true">
        <span :style="{ width: `${course.progress.percent}%` }" />
      </div>

      <div class="student-hero-actions">
        <RouterLink
          class="student-primary-button"
          :to="{
            name: STUDENT_STEP_ROUTE.name,
            params: { courseId: course.id, stepId: course.progress.next_step_id },
          }"
        >
          Продолжить <span aria-hidden="true">→</span>
        </RouterLink>
        <span class="student-hero-meta">{{ course.progress.percent }}% курса пройдено</span>
      </div>
    </template>

    <template v-else>
      <p class="student-hero-kicker">МОИ КУРСЫ</p>
      <h2>{{ hasCourses ? "Все доступные шаги пройдены" : "Пора начать обучение" }}</h2>
      <p class="student-hero-description">
        {{
          hasCourses
            ? "Можно вернуться к курсам, повторить материал или посмотреть результаты."
            : "Здесь появятся опубликованные курсы, на которые вас запишут."
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
  min-height: 294px;
  padding: 26px 28px;
  border-radius: 16px;
  background: radial-gradient(120% 140% at 100% 0%, #1e2f66 0%, #0b1220 60%);
  color: #fff;
}
.student-hero-kicker {
  margin: 0 0 10px;
  color: #7c95ff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.student-hero h2 {
  max-width: 760px;
  margin: 0;
  font-size: clamp(28px, 3vw, 36px);
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.1;
}
.student-hero-description {
  margin: 10px 0 0;
  color: #c9d5fc;
  font-size: 15px;
}
.student-progress-track {
  display: block;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
}
.student-progress-track > span {
  display: block;
  height: 100%;
  border-radius: inherit;
}
.student-progress-track--dark {
  width: 100%;
  margin-top: auto;
  background: #131c30;
}
.student-progress-track--dark > span {
  background: #7c95ff;
}
.student-hero-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
}
.student-primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 56px;
  padding: 0 32px;
  border-radius: 14px;
  background: #3457f0;
  color: #fff;
  font-size: 15px;
  font-weight: 750;
  text-decoration: none;
  transition:
    background 0.16s ease,
    transform 0.16s ease;
}
.student-primary-button:hover {
  background: #2949d2;
  transform: translateY(-1px);
}
.student-hero-meta {
  color: #c9d5fc;
  font-size: 15px;
}
@media (max-width: 640px) {
  .student-hero {
    min-height: 0;
    padding: 22px;
  }
  .student-hero h2,
  .student-hero-description {
    overflow-wrap: anywhere;
  }
  .student-hero h2 {
    font-size: 28px;
  }
  .student-progress-track--dark {
    margin-top: 24px;
  }
  .student-hero-actions {
    align-items: flex-start;
    flex-direction: column;
    width: 100%;
  }
  .student-primary-button {
    width: 100%;
  }
}
</style>
