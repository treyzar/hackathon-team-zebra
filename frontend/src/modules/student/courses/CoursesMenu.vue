<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { listCourses } from "./api";
import type { CourseListItem } from "./types";
import { STUDENT_COURSE_ROUTE } from "@/pages/student/course/constants";

const emit = defineEmits<{ navigate: [] }>();
const courses = ref<CourseListItem[]>([]);

onMounted(async () => {
  try {
    courses.value = await listCourses();
  } catch {
    // The menu still works without the shortcut list.
  }
});
</script>

<template>
  <section v-if="courses.length" class="courses-menu" aria-labelledby="courses-menu-heading">
    <h2 id="courses-menu-heading">МОИ КУРСЫ</h2>
    <RouterLink
      v-for="course in courses"
      :key="course.id"
      class="courses-menu-link"
      :class="{ 'courses-menu-link--new': !course.progress.steps_completed }"
      :to="{ name: STUDENT_COURSE_ROUTE.name, params: { courseId: course.id } }"
      @click="emit('navigate')"
    >
      <span>{{ course.title }}</span>
      <b v-if="course.progress.steps_completed"
        >{{ course.progress.steps_completed }}/{{ course.progress.steps_total }}</b
      >
      <span v-else class="courses-menu-state">не начат</span>
    </RouterLink>
  </section>
</template>

<style scoped>
.courses-menu {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
  padding: 14px;
  border-radius: 14px;
  background: var(--color-bg);
}
.courses-menu h2 {
  margin: 0;
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.courses-menu-link {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-text);
  font-size: 16px;
  text-decoration: none;
}
.courses-menu-link:hover {
  color: var(--color-primary);
}
.courses-menu-link > span:first-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.courses-menu-link b,
.courses-menu-state {
  flex: none;
}
.courses-menu-link--new {
  color: var(--color-muted);
}
</style>
