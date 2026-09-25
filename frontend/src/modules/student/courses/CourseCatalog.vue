<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useAuthStore } from "@/stores/auth";
import { studentCourseApi } from "./api";
import { documentTitle, errorMessage, stepDocument, stepLabels } from "./presentation";
import type { CourseListItem, StudentNotification } from "./types";
import CatalogGreeting from "./components/CatalogGreeting.vue";
import CatalogHero from "./components/CatalogHero.vue";
import CatalogSnapshot from "./components/CatalogSnapshot.vue";
import CourseCatalogCard from "./components/CourseCatalogCard.vue";

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

onMounted(load);
</script>

<template>
  <div class="student-catalog">
    <CatalogGreeting :username="auth.user?.username ?? ''" />

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
  max-width: 1450px;
  margin: 0 auto;
}
.student-catalog-top {
  display: flex;
  align-items: stretch;
  gap: 24px;
}
.student-catalog-top > :first-child {
  min-width: 0;
  flex: 1;
}
.student-section-heading {
  margin: 2px 0 12px;
}
.student-section-heading h2 {
  margin: 0;
  color: #0f172a;
  font-size: 24px;
  font-weight: 750;
  line-height: 1.25;
}
.student-course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}
.student-empty {
  padding: 28px;
  border: 1px dashed #cbd3e2;
  border-radius: 16px;
  background: #fff;
  color: #65728a;
}
.student-empty--error {
  background: #fff7f7;
  color: #a53b3b;
}
.student-empty button {
  margin-left: 8px;
  border: 0;
  background: transparent;
  color: #3457f0;
  font-weight: 700;
  cursor: pointer;
}
@media (max-width: 1100px) {
  .student-catalog-top {
    flex-direction: column;
  }
  .student-course-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 680px) {
  .student-course-grid {
    grid-template-columns: 1fr;
  }
}
</style>
