<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { studentCourseApi } from "./api";
import { documentTitle, errorMessage, stepDocument, stepLabels } from "./presentation";
import type { CourseListItem } from "./types";
import CatalogHero from "./components/CatalogHero.vue";
import CatalogSnapshot from "./components/CatalogSnapshot.vue";
import CourseCatalogCard from "./components/CourseCatalogCard.vue";

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
    courses.value = await studentCourseApi.listCourses();
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
        <CatalogSnapshot :courses="courses.length" :steps="totals.steps" :points="totals.points" />
      </div>

      <section aria-labelledby="student-courses-heading">
        <div class="student-section-heading">
          <h2 id="student-courses-heading">Мои курсы</h2>
          <span>{{ courses.length }}</span>
        </div>
        <div v-if="!courses.length" class="student-empty">Опубликованных курсов пока нет.</div>
        <div v-else class="student-course-grid">
          <CourseCatalogCard
            v-for="(course, index) in courses"
            :key="course.id"
            :course="course"
            :index="index"
          />
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
.student-section-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.student-section-heading h2 {
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
.student-course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
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
  color: #3457f0;
  font-weight: 700;
}
@media (max-width: 1000px) {
  .student-course-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .student-catalog-top {
    grid-template-columns: 1fr;
  }
  .student-course-grid {
    grid-template-columns: 1fr;
  }
}
</style>
