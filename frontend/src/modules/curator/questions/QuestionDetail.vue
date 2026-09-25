<script setup lang="ts">
import type { StudentStep } from "@/modules/student/courses/types";
import QuestionAnswerForm from "./QuestionAnswerForm.vue";
import QuestionTaskAccordion from "./QuestionTaskAccordion.vue";
import { questionAge, questionAuthor } from "./presentation";
import type { QuestionUpdate, StaffQuestion } from "./types";

defineProps<{
  question: StaffQuestion;
  similar: StaffQuestion[];
  stepLabel: (question: StaffQuestion) => string;
  step: StudentStep | null;
  stepLoading: boolean;
  stepError: string;
  saving: boolean;
}>();

const emit = defineEmits<{
  select: [id: number];
  loadStep: [];
  save: [changes: QuestionUpdate];
}>();
</script>

<template>
  <div class="question-detail">
    <div class="question-detail__breadcrumb">
      {{ question.course_title }} · {{ stepLabel(question) }}
    </div>
    <QuestionTaskAccordion
      :question-id="question.id"
      :step="step"
      :loading="stepLoading"
      :error="stepError"
      @load="emit('loadStep')"
    />
    <section class="question-detail__card question-detail__question">
      <div>
        <b>{{ questionAuthor(question) }}</b> <span>· {{ questionAge(question) }} назад</span>
      </div>
      <p>{{ question.text }}</p>
    </section>
    <section v-if="similar.length" class="question-detail__card question-detail__similar">
      <b>Похожие вопросы на этом шаге</b>
      <div v-for="item in similar.slice(0, 3)" :key="item.id">
        <button type="button" @click="emit('select', item.id)">
          {{ questionAuthor(item) }}: «{{ item.text }}»
        </button>
      </div>
    </section>
    <QuestionAnswerForm :question="question" :saving="saving" @save="emit('save', $event)" />
  </div>
</template>

<style scoped>
.question-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 860px;
}
.question-detail__breadcrumb {
  color: var(--color-muted);
}
.question-detail__card {
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: #fff;
}
.question-detail__question span {
  color: var(--color-muted);
}
.question-detail__question p {
  margin: 4px 0 0;
  font-size: 15px;
  white-space: pre-wrap;
}
.question-detail__similar {
  display: grid;
  gap: 4px;
  border-style: dashed;
  background: var(--color-bg);
}
.question-detail__similar button {
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-text);
  text-align: left;
  font: inherit;
  cursor: pointer;
}
.question-detail__similar button:hover {
  color: var(--color-primary);
}
</style>
