<script setup lang="ts">
import { computed, ref } from "vue";
import type { GroupCourseCoverage } from "../types";

const props = defineProps<{
  courses: GroupCourseCoverage[];
  loading: boolean;
  busy: boolean;
}>();

const emit = defineEmits<{
  enroll: [courseId: number];
}>();

const assigning = ref(false);
const selectedCourseId = ref<number | "">("");

const visibleCourses = computed(() => props.courses.filter((item) => item.enrolledCount > 0));

const selectableCourses = computed(() =>
  props.courses.filter((item) => item.studentsCount > 0 && item.enrolledCount < item.studentsCount),
);

function coverageLabel(item: GroupCourseCoverage): string {
  if (item.studentsCount === 0) return "нет учеников";
  if (item.enrolledCount === item.studentsCount) return "вся группа";
  return `${item.enrolledCount}/${item.studentsCount}`;
}

function submit(): void {
  if (selectedCourseId.value === "" || props.busy) return;
  emit("enroll", selectedCourseId.value);
  selectedCourseId.value = "";
  assigning.value = false;
}
</script>

<template>
  <div class="group-courses">
    <div class="group-courses__row">
      <strong>Курсы группы</strong>

      <span v-if="loading" class="group-courses__muted">Загрузка…</span>
      <template v-else>
        <span
          v-for="item in visibleCourses"
          :key="item.course.id"
          class="course-chip"
          :title="`Записано ${item.enrolledCount} из ${item.studentsCount} текущих учеников`"
        >
          {{ item.course.title }}
          <small v-if="item.enrolledCount < item.studentsCount">{{ coverageLabel(item) }}</small>
        </span>
        <span v-if="!visibleCourses.length" class="group-courses__muted"
          >Пока нет записанных учеников</span
        >
      </template>

      <button
        class="course-add"
        type="button"
        :disabled="busy || !selectableCourses.length"
        @click="assigning = !assigning"
      >
        + Назначить курс
      </button>
    </div>

    <form v-if="assigning" class="course-assign" @submit.prevent="submit">
      <select v-model="selectedCourseId" required>
        <option value="" disabled>Выберите курс</option>
        <option v-for="item in selectableCourses" :key="item.course.id" :value="item.course.id">
          {{ item.course.title }} · {{ coverageLabel(item) }}
        </option>
      </select>
      <button :disabled="busy || selectedCourseId === ''">Записать текущих учеников</button>
      <span>Новые ученики группы позже автоматически не запишутся.</span>
    </form>
  </div>
</template>

<style scoped>
.group-courses {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #edf0f6;
}
.group-courses__row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.group-courses__row > strong {
  margin-right: 4px;
  color: #1d2b43;
}
.course-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 11px;
  border-radius: 999px;
  background: #eef2ff;
  color: #273550;
  font-size: 13px;
  white-space: nowrap;
}
.course-chip small {
  color: #66718a;
}
.course-add {
  height: 32px;
  padding: 0 12px;
  border: 1px dashed #3457f0;
  border-radius: 999px;
  background: #fff;
  color: #3457f0;
  font:
    600 14px Onest,
    system-ui,
    sans-serif;
  cursor: pointer;
}
.course-add:disabled {
  border-color: #cbd3e2;
  color: #9aa4b6;
  cursor: default;
}
.group-courses__muted {
  color: #778197;
  font-size: 13px;
}
.course-assign {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
  padding: 10px;
  border-radius: 12px;
  background: #f7f9fd;
}
.course-assign select {
  min-width: 260px;
  height: 38px;
  padding: 0 11px;
  border: 1px solid #d9dfeb;
  border-radius: 10px;
  background: #fff;
  font: inherit;
}
.course-assign button {
  height: 38px;
  padding: 0 12px;
  border: 0;
  border-radius: 10px;
  background: #3457f0;
  color: #fff;
  font:
    600 13px Onest,
    system-ui,
    sans-serif;
}
.course-assign span {
  color: #6c768a;
  font-size: 12px;
}
</style>
