<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from "vue";

import QuestionDetail from "./QuestionDetail.vue";
import QuestionQueue from "./QuestionQueue.vue";
import { useQuestionQueue } from "./useQuestionQueue";
import { useQuestionSteps } from "./useQuestionSteps";

const {
  questions,
  filter,
  selectedId,
  loading,
  saving,
  error,
  saved,
  unansweredCount,
  visible,
  selected,
  similar,
  load,
  selectFilter,
  selectQuestion,
  save,
  dispose,
} = useQuestionQueue();
const {
  steps,
  loading: loadingSteps,
  errors: stepErrors,
  reset,
  loadStep,
  preload,
  label,
} = useQuestionSteps();

const selectedStep = computed(() =>
  selected.value ? (steps.value.get(selected.value.step_id) ?? null) : null,
);
const selectedStepLoading = computed(() =>
  selected.value ? loadingSteps.value.has(selected.value.step_id) : false,
);
const selectedStepError = computed(() =>
  selected.value ? (stepErrors.value.get(selected.value.step_id) ?? "") : "",
);

async function reload(): Promise<void> {
  reset();
  const items = await load();
  if (items) preload(items, selected.value?.step_id);
}

onMounted(reload);
onBeforeUnmount(() => {
  dispose();
  reset();
});
</script>

<template>
  <section class="questions-workspace" aria-label="Вопросы учеников">
    <QuestionQueue
      :questions="visible"
      :filter="filter"
      :selected-id="selectedId"
      :unanswered-count="unansweredCount"
      :loading="loading"
      :step-label="label"
      @filter="selectFilter"
      @select="selectQuestion"
    />
    <div class="questions-workspace__main">
      <div v-if="error" class="questions-workspace__error" role="alert">
        {{ error }}
        <button v-if="!questions.length" type="button" @click="reload">Повторить</button>
      </div>
      <p v-if="saved" class="questions-workspace__success" role="status">{{ saved }}</p>
      <div v-if="!selected && !loading && !error" class="questions-workspace__empty">
        {{ filter === "unanswered" ? "Все вопросы получили ответ." : "Выберите вопрос из списка." }}
      </div>
      <QuestionDetail
        v-if="selected"
        :key="selected.id"
        :question="selected"
        :similar="similar"
        :step-label="label"
        :step="selectedStep"
        :step-loading="selectedStepLoading"
        :step-error="selectedStepError"
        :saving="saving"
        @load-step="loadStep(selected.step_id)"
        @select="selectQuestion"
        @save="save"
      />
    </div>
  </section>
</template>

<style scoped>
.questions-workspace {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  background: var(--color-bg);
  font-size: 14px;
  line-height: 1.5;
}
.questions-workspace__main {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 24px;
}
.questions-workspace__error,
.questions-workspace__success,
.questions-workspace__empty {
  box-sizing: border-box;
  width: 100%;
  max-width: 860px;
}
.questions-workspace__error,
.questions-workspace__success {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
}
.questions-workspace__error {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.questions-workspace__error button {
  border: 0;
  background: none;
  color: var(--color-primary);
  font: inherit;
  cursor: pointer;
}
.questions-workspace__success {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.questions-workspace__empty {
  color: var(--color-muted);
}
@media (max-width: 760px) {
  .questions-workspace {
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: 100%;
  }
  .questions-workspace__main {
    overflow: visible;
    padding: 20px 16px 36px;
  }
}
</style>
