<script setup lang="ts">
import { RouterLink } from "vue-router";
import type { CourseListItem } from "../types";
import { progressText } from "../presentation";
import { STUDENT_COURSE_ROUTE } from "@/pages/student/course/constants";

defineProps<{ course: CourseListItem; index: number }>();
</script>

<template>
  <RouterLink
    class="student-course-card"
    :to="{ name: STUDENT_COURSE_ROUTE.name, params: { courseId: course.id } }"
  >
    <span
      class="student-course-mark"
      :class="`student-course-mark--${index % 3}`"
      aria-hidden="true"
      >{{ String(index + 1).padStart(2, "0") }}</span
    >
    <span class="student-course-kicker">КУРС · {{ course.progress.steps_total }} ШАГОВ</span>
    <strong>{{ course.title }}</strong>
    <span class="student-progress-track"
      ><span :style="{ width: `${course.progress.percent}%` }"
    /></span>
    <span class="student-course-bottom"
      >{{ progressText(course.progress.steps_completed, course.progress.steps_total) }}
      <span aria-hidden="true">↗</span></span
    >
  </RouterLink>
</template>

<style scoped>
.student-course-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 220px;
  padding: 24px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
  color: #0f172a;
  text-decoration: none;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}
.student-course-card:hover {
  transform: translateY(-2px);
  border-color: #c9d5fc;
  box-shadow: 0 12px 30px #21315a14;
}
.student-course-mark {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  margin-bottom: 24px;
  border-radius: 12px;
  background: #eaf0fe;
  color: #3457f0;
  font-weight: 800;
}
.student-course-mark--1 {
  background: #e4f5ec;
  color: #17915a;
}
.student-course-mark--2 {
  background: #fff1e6;
  color: #b8520f;
}
.student-course-kicker {
  margin-bottom: 8px;
  color: #738097;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
}
.student-course-card > strong {
  margin-bottom: 22px;
  font-size: 20px;
  line-height: 1.25;
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
  margin-top: 12px;
  color: #65728a;
  font-size: 13px;
}
</style>
