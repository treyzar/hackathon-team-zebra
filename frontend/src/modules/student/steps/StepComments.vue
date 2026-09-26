<script setup lang="ts">
import { ref, watch } from "vue";
import { getApiErrorMessage } from "@/api/errors";
import type { StudentQuestion } from "@/modules/student/courses/types.ts";
import { askQuestion, getStepQuestions } from "@/modules/student/courses/api.ts";

const props = defineProps<{ stepId: number }>();

const questions = ref<StudentQuestion[]>([]);
const newText = ref("");
const loading = ref(false);
const submitting = ref(false);
const error = ref("");

async function loadQuestions() {
  loading.value = true;
  error.value = "";
  try {
    questions.value = await getStepQuestions(props.stepId);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}

async function handleSubmit() {
  const text = newText.value.trim();
  if (!text) return;

  submitting.value = true;
  error.value = "";
  try {
    const created = await askQuestion(props.stepId, text);
    questions.value.unshift(created);
    newText.value = "";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    submitting.value = false;
  }
}

watch(() => props.stepId, loadQuestions, { immediate: true });
</script>

<template>
  <section class="step-comments">
    <h3>Вопросы и комментарии</h3>

    <form class="comments-form" @submit.prevent="handleSubmit">
      <textarea
        v-model="newText"
        placeholder="Задайте вопрос по этой задаче..."
        rows="3"
        :disabled="submitting"
        required
      />
      <div class="form-actions">
        <button type="submit" :disabled="submitting || !newText.trim()">
          {{ submitting ? "Отправка..." : "Отправить" }}
        </button>
      </div>
    </form>

    <div v-if="error" class="comments-error">{{ error }}</div>

    <div v-if="loading" class="comments-loading">Загрузка комментариев...</div>
    <div v-else-if="!questions.length" class="comments-empty">
      Пока нет вопросов к этой задаче. Будьте первыми!
    </div>

    <div v-else class="comments-list">
      <div v-for="q in questions" :key="q.id" class="comment-item">
        <div class="comment-header">
          <span class="comment-author">{{ q.is_mine ? "Вы" : "Ученик" }}</span>
          <time class="comment-date">{{ new Date(q.created_at).toLocaleString("ru-RU") }}</time>
        </div>
        <p class="comment-text">{{ q.text }}</p>

        <!-- Ответ куратора/преподавателя -->
        <div v-if="q.answer" class="comment-reply">
          <div class="reply-header">
            <strong>Ответ куратора:</strong>
            <time v-if="q.answered_at" class="comment-date">
              {{ new Date(q.answered_at).toLocaleString("ru-RU") }}
            </time>
          </div>
          <p class="reply-text">{{ q.answer }}</p>
        </div>
        <div v-else class="reply-pending">Ожидает ответа куратора</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.step-comments {
  margin-top: 36px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border, #e1e6f0);
}
.step-comments h3 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 700;
}
.comments-form textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 8px;
  font-family: inherit;
  font-size: var(--font-size-small);
  box-sizing: border-box;
  resize: vertical;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
.form-actions button {
  min-height: var(--button-height);
  padding: 8px 18px;
  background: var(--color-primary, #3457f0);
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font: 600 var(--font-size-base) var(--font-sans);
}
.form-actions button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.comments-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 20px;
}
.comment-item {
  padding: 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}
.comment-header {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-small);
  color: #64748b;
  margin-bottom: 6px;
}
.comment-author {
  font-weight: 600;
}
.comment-text {
  margin: 0;
  font-size: var(--font-size-base);
  white-space: pre-wrap;
}
.comment-reply {
  margin-top: 10px;
  padding: 10px 12px;
  background: #fff;
  border-left: 3px solid #3457f0;
  border-radius: 4px;
}
.reply-header {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-small);
  color: #3457f0;
  margin-bottom: 4px;
}
.reply-text {
  margin: 0;
  font-size: var(--font-size-base);
  white-space: pre-wrap;
}
.reply-pending {
  margin-top: 8px;
  font-size: var(--font-size-small);
  color: #94a3b8;
  font-style: italic;
}
.comments-loading,
.comments-empty {
  margin-top: 16px;
  font-size: var(--font-size-small);
  color: #64748b;
}
.comments-error {
  margin-top: 10px;
  color: #dc2626;
  font-size: var(--font-size-small);
}
@media (max-width: 680px) {
  .comment-header,
  .reply-header {
    flex-wrap: wrap;
    gap: 4px 10px;
  }
  .comment-text,
  .reply-text {
    overflow-wrap: anywhere;
  }
}
</style>
