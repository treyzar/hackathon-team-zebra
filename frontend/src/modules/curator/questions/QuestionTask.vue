<script setup lang="ts">
import { computed } from "vue";

import RichContent from "@/modules/student/courses/RichContent.vue";
import { stepDocument } from "@/modules/student/courses/presentation";
import type { StudentStep } from "@/modules/student/courses/types";

const props = defineProps<{ step: StudentStep }>();
const document = computed(() => stepDocument(props.step.type, props.step.content));
const options = computed(() =>
  Array.isArray(props.step.content.options)
    ? (props.step.content.options as { id: string; text: string }[])
    : [],
);
const samples = computed(() =>
  Array.isArray(props.step.content.samples)
    ? (props.step.content.samples as { input: string; output: string }[])
    : [],
);
const template = computed(() =>
  typeof props.step.content.template === "string" ? props.step.content.template : "",
);
</script>

<template>
  <div class="question-task">
    <RichContent v-if="document" :document="document" />
    <p v-else class="question-task__empty">Описание задания не заполнено.</p>
    <ol v-if="options.length" class="question-task__options">
      <li v-for="option in options" :key="option.id">{{ option.text }}</li>
    </ol>
    <div v-if="samples.length" class="question-task__samples">
      <h4>Примеры</h4>
      <div v-for="(sample, index) in samples" :key="index" class="question-task__sample">
        <strong>Пример {{ index + 1 }}</strong>
        <div>
          <span>Ввод</span>
          <pre>{{ sample.input || "Нет входных данных" }}</pre>
        </div>
        <div>
          <span>Вывод</span>
          <pre>{{ sample.output }}</pre>
        </div>
      </div>
    </div>
    <p v-if="step.type === 'programming'" class="question-task__limits">
      {{ step.content.time_limit_ms }} мс · {{ step.content.memory_limit_mb }} МБ
    </p>
    <pre v-if="template.trim()" class="question-task__template">{{ template }}</pre>
  </div>
</template>

<style scoped>
.question-task {
  display: grid;
  gap: 14px;
  min-width: 0;
  padding: 16px;
  border-top: 1px solid var(--color-border);
}
.question-task__empty {
  margin: 0;
  color: var(--color-muted);
}
.question-task__options {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 24px;
}
.question-task__samples {
  display: grid;
  gap: 10px;
}
.question-task__samples h4 {
  margin: 0;
}
.question-task__sample {
  display: grid;
  gap: 6px;
  padding: 12px;
  border-radius: 10px;
  background: var(--color-bg);
}
.question-task__sample span {
  color: var(--color-muted);
  font-size: 12px;
}
.question-task__sample pre {
  min-width: 0;
  overflow: auto;
  margin: 0;
  white-space: pre-wrap;
}
.question-task__limits {
  margin: 0;
  color: var(--color-muted);
}
.question-task__template {
  min-width: 0;
  overflow-x: auto;
  margin: 0;
  padding: 12px;
  border-radius: 10px;
  background: #101a32;
  color: #ecf1ff;
}
</style>
