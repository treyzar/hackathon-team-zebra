<script setup lang="ts">
import { computed } from "vue";

import {
  activityLabel,
  lagLabel,
  moduleCell,
  studentCourseProgress,
  studentName,
} from "./presentation";
import type { CourseAnalytics } from "./types";

const props = defineProps<{ data: CourseAnalytics }>();
const emit = defineEmits<{ selectModule: [moduleId: number] }>();
const gridStyle = computed(() => ({
  gridTemplateColumns: `minmax(190px, 1.6fr) ${props.data.modules.map(() => "minmax(130px, 1fr)").join(" ")} minmax(140px, 1.3fr) 120px 110px`,
  minWidth: `${Math.max(860, 520 + props.data.modules.length * 145)}px`,
}));
</script>

<template>
  <div class="analytics-card analytics-module-card">
    <div class="analytics-card-heading">
      <h3>Личный прогресс</h3>
      <span>нажмите на модуль в шапке, чтобы открыть его шаги</span>
    </div>
    <div class="analytics-table-scroll">
      <div class="analytics-table-head analytics-dynamic-grid" :style="gridStyle">
        <span>УЧЕНИК</span>
        <button
          v-for="module in data.modules"
          :key="module.module_id"
          type="button"
          class="analytics-column-link"
          @click="emit('selectModule', module.module_id)"
        >
          {{ module.title }} ›
        </button>
        <span>ВЕСЬ КУРС</span><span>ОТСТАВАНИЕ</span><span>АКТИВНОСТЬ</span>
      </div>
      <div
        v-for="student in data.students"
        :key="student.student_id"
        class="analytics-student-row analytics-dynamic-grid"
        :style="gridStyle"
      >
        <strong>{{ studentName(student) }}</strong>
        <span
          v-for="module in data.modules"
          :key="module.module_id"
          class="analytics-state-cell"
          :class="`analytics-state-cell--${moduleCell(student, module.module_id)?.has_unresolved_return ? 'return' : (moduleCell(student, module.module_id)?.state ?? 'not_started')}`"
        >
          {{
            moduleCell(student, module.module_id)?.state === "not_started"
              ? "не начат"
              : `${moduleCell(student, module.module_id)?.steps_completed ?? 0}/${moduleCell(student, module.module_id)?.steps_total ?? 0}`
          }}
        </span>
        <span class="analytics-course-progress">
          <span class="analytics-progress-track"
            ><span :style="{ width: `${studentCourseProgress(student).percent}%` }"
          /></span>
          <span
            >{{ studentCourseProgress(student).completed }}/{{
              studentCourseProgress(student).total
            }}</span
          >
        </span>
        <span class="analytics-pill" :class="`analytics-pill--${student.lag.status}`">{{
          lagLabel(student.lag.status)
        }}</span>
        <span class="analytics-muted">{{ activityLabel(student.last_submission_at) }}</span>
      </div>
    </div>
    <div v-if="!data.students.length" class="analytics-empty">
      В группе пока нет учеников на этом курсе.
    </div>
    <p class="analytics-table-note">
      В ячейке модуля показано число зачтённых шагов. Возвраты выделены оранжевым.
    </p>
  </div>
</template>
