<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { questionUpdate } from "./presentation";
import type { QuestionUpdate, QuestionVisibility, StaffQuestion } from "./types";

const props = defineProps<{ question: StaffQuestion; saving: boolean }>();
const emit = defineEmits<{ save: [changes: QuestionUpdate] }>();
const answer = ref("");
const visibility = ref<QuestionVisibility>("private");

watch(
  () => props.question,
  (question) => {
    answer.value = question.answer ?? "";
    visibility.value = question.visibility;
  },
  { immediate: true },
);

const changes = computed(() => questionUpdate(props.question, answer.value, visibility.value));
const canSave = computed(
  () =>
    props.question.can_answer &&
    !props.saving &&
    answer.value.trim().length > 0 &&
    answer.value.length <= 10_000 &&
    Object.keys(changes.value).length > 0,
);

function save(): void {
  if (canSave.value) emit("save", changes.value);
}
</script>

<template>
  <div class="question-answer-form">
    <label for="curator-question-answer">Ответ</label>
    <textarea
      id="curator-question-answer"
      v-model="answer"
      rows="4"
      maxlength="10000"
      :readonly="!question.can_answer"
      placeholder="Напишите ответ ученику…"
    />
    <div class="question-answer-form__visibility">
      <button
        class="question-answer-form__switch"
        :class="{ 'question-answer-form__switch--on': visibility === 'course' }"
        type="button"
        role="switch"
        :aria-checked="visibility === 'course'"
        aria-label="Показать ответ всем на этом шаге"
        :disabled="!question.can_answer"
        @click="visibility = visibility === 'course' ? 'private' : 'course'"
      />
      <div>
        <strong>Показать ответ всем на этом шаге</strong>
        <p v-if="visibility === 'course'">
          Вопрос и ответ увидят все ученики, которым доступен шаг.
        </p>
        <p v-else-if="visibility === 'group'">Сейчас вопрос и ответ видны группе автора.</p>
        <p v-else>Ответ будет виден только автору вопроса.</p>
      </div>
    </div>
    <p v-if="!question.can_answer" class="question-answer-form__notice">
      Это публичный вопрос другой группы. Ответ можно только прочитать.
    </p>
    <div v-else class="question-answer-form__actions">
      <button type="button" :disabled="!canSave" @click="save">
        {{
          saving
            ? "Сохраняем…"
            : question.answer === null
              ? "Опубликовать ответ"
              : "Сохранить изменения"
        }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.question-answer-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.question-answer-form > label {
  font-weight: 600;
}
.question-answer-form > textarea {
  box-sizing: border-box;
  min-height: 110px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: #fff;
  color: var(--color-text);
  font: 15px/1.55 var(--font-sans);
  resize: vertical;
}
.question-answer-form__visibility {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: #fff;
}
.question-answer-form__visibility p {
  margin: 3px 0 0;
  color: var(--color-muted);
  font-size: 13px;
}
.question-answer-form__switch {
  position: relative;
  width: 40px;
  height: 24px;
  flex: none;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: #c9cdd8;
  cursor: pointer;
}
.question-answer-form__switch::after {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  content: "";
  transition: left 0.15s;
}
.question-answer-form__switch--on {
  background: var(--color-primary);
}
.question-answer-form__switch--on::after {
  left: 19px;
}
.question-answer-form__switch:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.question-answer-form__notice {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-neutral-soft);
  color: var(--color-muted);
}
.question-answer-form__actions {
  display: flex;
  justify-content: flex-end;
}
.question-answer-form__actions button {
  min-height: 40px;
  padding: 0 16px;
  border: 0;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font: 600 14px var(--font-sans);
  cursor: pointer;
}
.question-answer-form__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
