<script setup lang="ts">
import { computed } from "vue";

import {
  activityLabel,
  stepCell,
  stepCellStatus,
  stepTypeLabel,
  studentLastSubmission,
  studentName,
} from "./presentation";
import type { ModuleAnalytics } from "./types";

const props = defineProps<{ data: ModuleAnalytics; moduleNumber: number }>();
const emit = defineEmits<{ selectStep: [stepId: number] }>();
const gridStyle = computed(() => ({
  gridTemplateColumns: `200px ${props.data.steps.map(() => "minmax(84px, 1fr)").join(" ")}`,
  minWidth: `${Math.max(640, 220 + props.data.steps.length * 92)}px`,
}));

function completedPercent(stepId: number): number {
  if (!props.data.students.length) return 0;
  const completed = props.data.students.filter(
    (student) => stepCell(student, stepId)?.completed,
  ).length;
  return Math.round((100 * completed) / props.data.students.length);
}
</script>

<template>
  <div class="analytics-card analytics-module-card">
    <div class="analytics-card-heading">
      <h3>{{ data.module.title }} · ученики по шагам</h3>
      <span>нажмите на шаг в шапке, чтобы разобрать его</span>
    </div>
    <div class="analytics-table-scroll">
      <div
        class="analytics-table-head analytics-dynamic-grid analytics-matrix-row"
        :style="gridStyle"
      >
        <span class="analytics-sticky-name">УЧЕНИК</span>
        <button
          v-for="step in data.steps"
          :key="step.step_id"
          type="button"
          class="analytics-column-link analytics-step-column"
          :title="step.title"
          @click="emit('selectStep', step.step_id)"
        >
          <strong>{{ moduleNumber }}.{{ step.position }}</strong>
          <small>{{ stepTypeLabel(step.type) }}</small>
        </button>
      </div>
      <div
        v-for="student in data.students"
        :key="student.student_id"
        class="analytics-student-row analytics-dynamic-grid analytics-matrix-row"
        :style="gridStyle"
      >
        <span class="analytics-sticky-name analytics-student-identity">
          <strong>{{ studentName(student) }}</strong>
          <small>{{ activityLabel(studentLastSubmission(student)) }}</small>
        </span>
        <span
          v-for="step in data.steps"
          :key="step.step_id"
          class="analytics-state-cell"
          :class="`analytics-state-cell--${stepCellStatus(stepCell(student, step.step_id)).tone}`"
          :title="`${step.title}: ${stepCellStatus(stepCell(student, step.step_id)).text}`"
          >{{ stepCellStatus(stepCell(student, step.step_id)).text }}</span
        >
      </div>
      <div
        class="analytics-table-head analytics-dynamic-grid analytics-matrix-row analytics-matrix-footer"
        :style="gridStyle"
      >
        <strong>Выполнили шаг, %</strong>
        <strong v-for="step in data.steps" :key="step.step_id"
          >{{ completedPercent(step.step_id) }}%</strong
        >
      </div>
    </div>
    <div v-if="!data.steps.length" class="analytics-empty">В модуле пока нет шагов.</div>
    <p class="analytics-table-note">
      ✓ зачтено · ◷ на проверке · ↺ возвращено · × не прошло · – не начато
    </p>
  </div>
</template>
