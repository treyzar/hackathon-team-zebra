<script setup lang="ts">
import { RouterLink } from "vue-router";
import type { CourseListItem } from "../types";
import { pointsText, progressText } from "../presentation";
import { STUDENT_COURSE_ROUTE } from "@/pages/student/course/constants";

defineProps<{ course: CourseListItem }>();
</script>

<template>
  <RouterLink
    class="student-course-card"
    :to="{ name: STUDENT_COURSE_ROUTE.name, params: { courseId: course.id } }"
  >
    <span class="student-course-kicker">КУРС · {{ course.progress.steps_total }} ШАГОВ</span>
    <strong>{{ course.title }}</strong>

    <span class="student-progress-track" aria-hidden="true">
      <span :style="{ width: `${course.progress.percent}%` }" />
    </span>

    <span class="student-course-bottom">
      <span v-if="course.progress.steps_completed">
        {{ progressText(course.progress.steps_completed, course.progress.steps_total) }}
      </span>
      <span v-else>○ Не начато</span>
      <b>{{ pointsText(course.progress.points_earned) }}</b>
    </span>
  </RouterLink>
</template>

<style scoped>
.student-course-card {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-height: 142px;
  padding: 18px 20px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
  color: #0f172a;
  text-decoration: none;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.16s ease;
}
.student-course-card:hover {
  transform: translateY(-1px);
  border-color: #c9d5fc;
  box-shadow: 0 10px 28px #15274b10;
}
.student-course-card:focus-visible {
  outline: 3px solid #3457f0;
  outline-offset: 2px;
}
.student-course-kicker {
  color: #4a546b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.student-course-card > strong {
  font-size: 16px;
  line-height: 1.35;
}
.student-progress-track {
  display: block;
  height: 8px;
  margin-top: auto;
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
.student-course-bottom {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #4a546b;
  font-size: 14px;
}
.student-course-bottom b {
  color: #0f172a;
  white-space: nowrap;
}
</style>
