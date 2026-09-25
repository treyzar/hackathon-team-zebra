<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { courseApi } from "./api";
import type { Course } from "../shared/types";
import { ADMIN_COURSE_ROUTE } from "@/pages/admin/course/constants";
import { ADMIN_COURSES_ROUTE } from "@/pages/admin/courses/constants";

const courses = ref<Course[]>([]);
const loading = ref(true);
const error = ref("");
onMounted(async () => {
  try {
    courses.value = await courseApi.courses();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="admin-page">
    <Teleport to="#admin-page-header">
      <div class="admin-toolbar">
        <div>
          <h2>Конструктор курсов</h2>
          <p>Откройте курс, чтобы изменить структуру и задания.</p>
        </div>
        <RouterLink class="admin-button admin-button--primary" :to="ADMIN_COURSES_ROUTE.path"
          >+ Новый курс</RouterLink
        >
      </div>
    </Teleport>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <div v-if="loading" class="admin-panel admin-empty">Загружаем курсы…</div>
    <div v-else-if="!courses.length" class="admin-panel admin-empty">
      Курсов пока нет. Создайте первый курс.
    </div>
    <div v-else class="admin-workspace-grid">
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Курс</th>
              <th>Статус</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="course in courses" :key="course.id">
              <td>
                <strong>{{ course.title }}</strong
                ><small>{{ course.slug }}</small>
              </td>
              <td>
                <span
                  class="admin-badge"
                  :class="course.is_published ? 'admin-badge--green' : 'admin-badge--gray'"
                  >{{ course.is_published ? "✓ Опубликован" : "○ Черновик" }}</span
                >
              </td>
              <td>
                <RouterLink :to="{ name: ADMIN_COURSE_ROUTE.name, params: { courseId: course.id } }"
                  >Открыть →</RouterLink
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <aside class="admin-rail-card">
        <h3>Конструктор</h3>
        <p>Выберите курс. Внутри можно менять модули, порядок шагов и содержание заданий.</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.admin-table {
  min-width: 550px;
}
</style>
