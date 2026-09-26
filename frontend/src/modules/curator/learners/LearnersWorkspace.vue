<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getApiErrorMessage } from "@/api/errors";
import { lagLabel, studentName } from "../analytics/presentation";
import "../analytics/analytics.css";
import { learnersApi } from "./api";
import { overdueText, sortLearners, statusCounts } from "./presentation";
import type { LearnerGroup } from "./types";

const groups = ref<LearnerGroup[]>([]);
const loading = ref(true);
const error = ref("");

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    groups.value = await learnersApi.groups();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="learners" aria-label="Ученики групп">
    <div class="learners-head">
      <h2>Ученики</h2>
      <p>Статус ученика — худший из его курсов: сначала те, кому нужно внимание.</p>
    </div>

    <p v-if="loading" class="learners-state" role="status">Загружаем группы…</p>
    <p v-else-if="error" class="learners-state learners-state--error" role="alert">
      {{ error }} <button type="button" @click="load">Повторить</button>
    </p>
    <p v-else-if="!groups.length" class="learners-state">За вами пока нет групп.</p>

    <article v-for="group in groups" :key="group.group_id" class="learners-group">
      <header class="learners-group-head">
        <h3>{{ group.name }}</h3>
        <span class="learners-count">Учеников: {{ group.students.length }}</span>
        <span class="analytics-pills">
          <span
            v-for="(count, status) in statusCounts(group.students)"
            v-show="count"
            :key="status"
            class="analytics-pill"
            :class="`analytics-pill--${status}`"
            >{{ lagLabel(status) }}: {{ count }}</span
          >
        </span>
      </header>

      <p v-if="!group.students.length" class="learners-empty">В группе пока нет учеников.</p>
      <ul v-else class="learners-list">
        <li v-for="student in sortLearners(group.students)" :key="student.student_id">
          <div class="learners-student">
            <strong :title="student.username">{{ studentName(student) }}</strong>
            <span
              v-if="student.status"
              class="analytics-pill"
              :class="`analytics-pill--${student.status}`"
              >{{ lagLabel(student.status) }}</span
            >
            <span v-else class="learners-muted">Не записан на курсы</span>
          </div>
          <ul v-if="student.courses.length" class="learners-courses">
            <li v-for="course in student.courses" :key="course.course_id">
              <span>{{ course.title }}</span>
              <span :class="`learners-course--${course.status}`">{{
                lagLabel(course.status)
              }}</span>
              <span v-if="course.overdue_steps" class="learners-muted">{{
                overdueText(course.overdue_steps)
              }}</span>
            </li>
          </ul>
        </li>
      </ul>
    </article>
  </section>
</template>

<style scoped>
.learners {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 1100px;
  margin: 0 auto;
  color: #0f172a;
  font-size: 14px;
  line-height: 1.5;
}
.learners-head h2 {
  margin: 0;
  font-size: 22px;
}
.learners-head p,
.learners-muted,
.learners-count,
.learners-empty {
  margin: 0;
  color: #4a546b;
}
.learners-state {
  padding: 48px 24px;
  border: 1px dashed #cbd3e2;
  border-radius: 16px;
  color: #4a546b;
  text-align: center;
}
.learners-state--error {
  color: #9a3c3c;
}
.learners-group {
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.learners-group-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 14px;
  padding: 14px 16px;
  border-bottom: 1px solid #edf0f6;
}
.learners-group-head h3 {
  margin: 0;
  font-size: 16px;
}
.learners-empty {
  padding: 20px 16px;
}
.learners-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.learners-list > li {
  padding: 12px 16px;
  border-top: 1px solid #edf0f6;
}
.learners-list > li:first-child {
  border-top: 0;
}
.learners-student {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 12px;
}
.learners-courses {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
  font-size: 13px;
}
.learners-courses li {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
}
.learners-course--falling_behind {
  color: #b8520f;
  font-weight: 600;
}
.learners-course--slowed {
  color: #4a546b;
  font-weight: 600;
}
.learners-course--on_track {
  color: #17915a;
}
</style>
