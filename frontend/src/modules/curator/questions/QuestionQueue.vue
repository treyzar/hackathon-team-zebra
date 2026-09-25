<script setup lang="ts">
import { questionAge, questionAuthor } from "./presentation";
import type { QuestionFilter, StaffQuestion } from "./types";

defineProps<{
  questions: StaffQuestion[];
  filter: QuestionFilter;
  selectedId: number | null;
  unansweredCount: number;
  loading: boolean;
  stepLabel: (question: StaffQuestion) => string;
}>();

const emit = defineEmits<{
  select: [id: number];
  filter: [value: QuestionFilter];
}>();
</script>

<template>
  <aside class="question-queue" aria-label="Список вопросов">
    <div class="question-queue__tabs" role="group" aria-label="Фильтр вопросов">
      <button
        type="button"
        :class="{ 'question-queue__tab--active': filter === 'unanswered' }"
        :aria-pressed="filter === 'unanswered'"
        @click="emit('filter', 'unanswered')"
      >
        Без ответа · {{ unansweredCount }}
      </button>
      <button
        type="button"
        :class="{ 'question-queue__tab--active': filter === 'all' }"
        :aria-pressed="filter === 'all'"
        @click="emit('filter', 'all')"
      >
        Все
      </button>
    </div>
    <div v-if="loading" class="question-queue__state" role="status">Загружаем вопросы…</div>
    <div v-else-if="!questions.length" class="question-queue__state">
      {{ filter === "unanswered" ? "Вопросов без ответа нет." : "Вопросов пока нет." }}
    </div>
    <nav v-else class="question-queue__items" aria-label="Вопросы">
      <button
        v-for="question in questions"
        :key="question.id"
        class="question-queue__item"
        :class="{ 'question-queue__item--selected': question.id === selectedId }"
        type="button"
        :aria-pressed="question.id === selectedId"
        @click="emit('select', question.id)"
      >
        <span class="question-queue__item-head">
          <b>{{ questionAuthor(question) }}</b>
          <time :datetime="question.created_at">{{ questionAge(question) }}</time>
        </span>
        <small>{{ stepLabel(question) }}</small>
        <span class="question-queue__item-text">{{ question.text }}</span>
        <span v-if="question.answer !== null" class="question-queue__badge">С ответом</span>
        <span v-if="!question.can_answer" class="question-queue__badge question-queue__badge--muted"
          >Только чтение</span
        >
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.question-queue {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  padding: 24px 14px;
  border-right: 1px solid var(--color-border);
}
.question-queue h2 {
  margin: 0 0 4px;
  font-size: 28px;
  line-height: 1.2;
}
.question-queue__tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 4px;
}
.question-queue__tabs button {
  padding: 4px 10px;
  border: 0;
  border-radius: 999px;
  background: #fff;
  color: var(--color-muted);
  font: 600 13px var(--font-sans);
  white-space: nowrap;
  cursor: pointer;
}
.question-queue__tabs .question-queue__tab--active {
  background: var(--color-text);
  color: #fff;
}
.question-queue__items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
  padding: 2px;
}
.question-queue__state {
  padding: 16px 10px;
  color: var(--color-muted);
}
.question-queue__item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: #fff;
  color: var(--color-text);
  text-align: left;
  font: inherit;
  cursor: pointer;
}
.question-queue__item:hover {
  border-color: var(--color-primary-pale);
}
.question-queue__item--selected,
.question-queue__item--selected:hover {
  border: 2px solid var(--color-primary);
  padding: 9px 11px;
  background: var(--color-primary-soft);
}
.question-queue__item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.question-queue__item-head time,
.question-queue__item small {
  color: var(--color-muted);
  font-size: 12px;
}
.question-queue__item-text {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}
.question-queue__badge {
  width: max-content;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--color-success-soft);
  color: var(--color-success);
  font-size: 12px;
  font-weight: 600;
}
.question-queue__badge--muted {
  background: var(--color-neutral-soft);
  color: var(--color-neutral);
}
@media (max-width: 760px) {
  .question-queue {
    max-height: 320px;
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
