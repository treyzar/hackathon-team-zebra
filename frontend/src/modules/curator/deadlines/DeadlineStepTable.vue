<script setup lang="ts">
import {
  deadlineDate,
  deadlineLabel,
  deadlineTime,
  stepTypeLabel,
  withDeadlineDate,
  withDeadlineTime,
} from "./presentation";
import type { DeadlineModule, StepDeadline } from "./types";

const props = defineProps<{
  groupName: string;
  modules: DeadlineModule[];
  drafts: Record<number, string | null>;
  disabled: boolean;
}>();

const emit = defineEmits<{ update: [stepId: number, value: string | null] }>();

function draft(row: StepDeadline): string | null {
  return props.drafts[row.step_id] ?? null;
}

function changeDate(row: StepDeadline, event: Event): void {
  emit(
    "update",
    row.step_id,
    withDeadlineDate(draft(row), (event.target as HTMLInputElement).value),
  );
}

function changeTime(row: StepDeadline, event: Event): void {
  emit(
    "update",
    row.step_id,
    withDeadlineTime(draft(row), (event.target as HTMLInputElement).value),
  );
}
</script>

<template>
  <section class="deadlines-step-card" aria-label="Дедлайны шагов">
    <div class="deadlines-step-head">
      <span>ШАГ</span>
      <span></span>
      <span>ТИП</span>
      <span>СРОК ДЛЯ {{ groupName.toUpperCase() }}</span>
    </div>
    <div v-if="!modules.length" class="deadlines-empty">В этом курсе пока нет открытых шагов.</div>
    <div v-for="module in modules" :key="module.id" class="deadlines-module">
      <h3>{{ module.number }}. {{ module.title }}</h3>
      <div v-for="item in module.steps" :key="item.deadline.step_id" class="deadlines-step-row">
        <span class="deadlines-step-number">{{ item.number }}</span>
        <strong>{{ item.deadline.title || `Шаг #${item.deadline.step_id}` }}</strong>
        <span class="deadlines-step-type">{{ stepTypeLabel(item.deadline.type) }}</span>
        <div class="deadlines-step-control">
          <div v-if="draft(item.deadline) !== null" class="deadlines-date-fields">
            <input
              type="date"
              :value="deadlineDate(draft(item.deadline))"
              :disabled="disabled"
              :aria-label="`Дата для шага ${item.number}`"
              @input="changeDate(item.deadline, $event)"
            />
            <input
              type="time"
              :value="deadlineTime(draft(item.deadline))"
              :disabled="disabled || !deadlineDate(draft(item.deadline))"
              :aria-label="`Время для шага ${item.number}`"
              @input="changeTime(item.deadline, $event)"
              class="min-w-20!"
            />
            <button
              type="button"
              class="deadlines-clear"
              :disabled="disabled"
              :aria-label="`Убрать отдельный срок для шага ${item.number}`"
              @click="emit('update', item.deadline.step_id, null)"
            >
              ×
            </button>
          </div>
          <template v-else>
            <button
              type="button"
              class="deadlines-add"
              :disabled="disabled"
              @click="emit('update', item.deadline.step_id, '')"
            >
              + задать срок
            </button>
            <small v-if="item.deadline.effective" class="deadlines-inherited">
              Сейчас: {{ deadlineLabel(item.deadline.effective.due_at) }}
            </small>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>
