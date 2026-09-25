<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import { CURATOR_REVIEWS_ROUTE } from "@/pages/curator/reviews/constants";
import {
  activityLabel,
  stepCell,
  stepCellStatus,
  stepSummary,
  stepTypeLabel,
  studentName,
} from "./presentation";
import type { ModuleAnalytics, StepColumn } from "./types";

const props = defineProps<{ data: ModuleAnalytics; step: StepColumn; moduleNumber: number }>();
const summary = computed(() => stepSummary(props.data, props.step.step_id));
const funnel = computed(() => [
  { label: "учеников в группе", value: summary.value.total },
  { label: "сдали хотя бы раз", value: summary.value.submitted },
  { label: "решили с 1-й попытки", value: summary.value.firstAttempt },
  { label: "зачли шаг", value: summary.value.completed },
]);
const issues = computed(() => [
  { label: "Возвращено на доработку", value: summary.value.returned },
  { label: "Не прошло проверку", value: summary.value.failed },
  { label: "На проверке", value: summary.value.checking },
]);
</script>

<template>
  <h2 class="analytics-step-title">{{ moduleNumber }}.{{ step.position }} {{ step.title }}</h2>
  <div class="analytics-step-layout">
    <div class="analytics-step-main">
      <div class="analytics-card analytics-step-card">
        <div class="analytics-card-heading">
          <h3>Путь учеников по шагу</h3>
          <span>{{ stepTypeLabel(step.type) }}</span>
        </div>
        <div class="analytics-funnel">
          <div v-for="item in funnel" :key="item.label">
            <strong>{{ item.value }}</strong>
            <span class="analytics-progress-track"
              ><span
                :style="{ width: `${summary.total ? (100 * item.value) / summary.total : 0}%` }"
            /></span>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </div>
      <div class="analytics-step-charts">
        <div class="analytics-card analytics-step-card">
          <h3>Сколько попыток сделали</h3>
          <div class="analytics-attempts">
            <div v-for="(count, index) in summary.attempts" :key="index">
              <strong>{{ count }}</strong>
              <span
                :style="{
                  height: `${Math.max(4, (70 * count) / Math.max(1, ...summary.attempts))}px`,
                }"
              />
              <small>{{ index === 3 ? "4+" : index + 1 }} попыт.</small>
            </div>
          </div>
        </div>
        <div class="analytics-card analytics-step-card">
          <h3>Текущие состояния</h3>
          <div v-for="issue in issues" :key="issue.label" class="analytics-issue">
            <span>{{ issue.label }}</span
            ><strong>{{ issue.value }}</strong>
            <span class="analytics-progress-track"
              ><span
                :style="{ width: `${summary.total ? (100 * issue.value) / summary.total : 0}%` }"
            /></span>
          </div>
        </div>
      </div>
      <p class="analytics-step-note">
        Подробные причины ошибок и возвратов пока не входят в аналитику.
      </p>
    </div>
    <aside class="analytics-card analytics-step-students">
      <div class="analytics-card-heading">
        <h3>Ученики на шаге</h3>
        <span>попытки · когда</span>
      </div>
      <div
        v-for="student in data.students"
        :key="student.student_id"
        class="analytics-step-student"
      >
        <strong>{{ studentName(student) }}</strong>
        <span
          class="analytics-state-cell"
          :class="`analytics-state-cell--${stepCellStatus(stepCell(student, step.step_id)).tone}`"
          >{{ stepCellStatus(stepCell(student, step.step_id)).text }}</span
        >
        <span>{{ stepCell(student, step.step_id)?.attempts ?? 0 }}</span>
        <small>{{
          activityLabel(stepCell(student, step.step_id)?.last_submission_at ?? null)
        }}</small>
      </div>
      <RouterLink :to="CURATOR_REVIEWS_ROUTE.path" class="analytics-reviews-link"
        >Открыть работы на проверке →</RouterLink
      >
    </aside>
  </div>
</template>
