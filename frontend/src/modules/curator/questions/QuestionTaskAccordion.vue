<script setup lang="ts">
import { ref } from "vue";

import type { StudentStep } from "@/modules/student/courses/types";
import QuestionTask from "./QuestionTask.vue";

defineProps<{
  questionId: number;
  step: StudentStep | null;
  loading: boolean;
  error: string;
}>();
const emit = defineEmits<{ load: [] }>();
const open = ref(false);

function toggle(): void {
  open.value = !open.value;
  if (open.value) emit("load");
}
</script>

<template>
  <section class="question-task-accordion">
    <button
      class="question-task-accordion__toggle"
      type="button"
      :aria-expanded="open"
      :aria-controls="`question-task-${questionId}`"
      @click="toggle"
    >
      <span>Условие задания</span>
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path
          d="m5 7.5 5 5 5-5"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>
    <div v-if="open" :id="`question-task-${questionId}`">
      <QuestionTask v-if="step" :step="step" />
      <div v-else class="question-task-accordion__state">
        <template v-if="loading">Загружаем задание…</template>
        <template v-else>{{ error || "Задание пока недоступно." }}</template>
        <button v-if="!loading" type="button" @click="emit('load')">Повторить</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.question-task-accordion {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: #fff;
}
.question-task-accordion__toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 12px 16px;
  border: 0;
  background: transparent;
  color: var(--color-text);
  text-align: left;
  font: 600 14px var(--font-sans);
  cursor: pointer;
}
.question-task-accordion__toggle svg {
  width: 20px;
  height: 20px;
  transition: transform 0.15s;
}
.question-task-accordion__toggle[aria-expanded="true"] svg {
  transform: rotate(180deg);
}
.question-task-accordion__state {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--color-border);
  color: var(--color-muted);
}
.question-task-accordion__state button {
  border: 0;
  background: none;
  color: var(--color-primary);
  font: inherit;
  cursor: pointer;
}
</style>
