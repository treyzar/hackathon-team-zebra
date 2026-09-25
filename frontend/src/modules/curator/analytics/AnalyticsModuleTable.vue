<script setup lang="ts">
import type { ModuleStats } from "./types";

defineProps<{
  modules: ModuleStats[];
  studentsTotal: number;
  stepCounts: Record<number, number>;
}>();
const emit = defineEmits<{ select: [moduleId: number] }>();
</script>

<template>
  <div class="analytics-table-scroll">
    <div class="analytics-table-head analytics-module-grid" aria-hidden="true">
      <span>МОДУЛЬ</span>
      <span>УЧЕНИКИ: ПРОШЛИ · В ПРОЦЕССЕ · НЕ НАЧАЛИ</span>
      <span>С 1-Й ПОПЫТКИ</span>
      <span>ПОПЫТОК</span>
      <span>ВОЗВРАТОВ</span>
      <span></span>
    </div>
    <button
      v-for="module in modules"
      :key="module.module_id"
      type="button"
      class="analytics-table-row analytics-module-grid"
      @click="emit('select', module.module_id)"
    >
      <span>
        <strong>{{ module.title }}</strong>
        <small>{{ stepCounts[module.module_id] ?? 0 }} шагов</small>
      </span>
      <span class="analytics-module-split">
        <span class="analytics-split-bar" aria-hidden="true">
          <span
            class="analytics-split-bar__passed"
            :style="{
              width: `${studentsTotal ? (100 * module.students_passed) / studentsTotal : 0}%`,
            }"
          />
          <span
            class="analytics-split-bar__progress"
            :style="{
              width: `${studentsTotal ? (100 * module.students_in_progress) / studentsTotal : 0}%`,
            }"
          />
          <span
            class="analytics-split-bar__idle"
            :style="{
              width: `${studentsTotal ? (100 * module.students_not_started) / studentsTotal : 0}%`,
            }"
          />
        </span>
        <small
          >{{ module.students_passed }} · {{ module.students_in_progress }} ·
          {{ module.students_not_started }}</small
        >
      </span>
      <span
        :class="{
          'analytics-warning-text':
            module.first_attempt_percent !== null && module.first_attempt_percent < 50,
        }"
      >
        {{ module.first_attempt_percent === null ? "—" : `${module.first_attempt_percent}%` }}
      </span>
      <span>{{
        module.avg_attempts === null ? "—" : module.avg_attempts.toLocaleString("ru-RU")
      }}</span>
      <span :class="{ 'analytics-warning-text': module.returns > 0 }">{{ module.returns }}</span>
      <span class="analytics-chevron" aria-hidden="true">›</span>
    </button>
  </div>
</template>
