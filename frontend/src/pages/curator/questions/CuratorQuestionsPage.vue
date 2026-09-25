<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { getApiErrorMessage } from "@/api/errors";
import { questionApi } from "@/modules/curator/questions/api";
import QuestionTask from "@/modules/curator/questions/QuestionTask.vue";
import {
  questionAge,
  questionAuthor,
  questionUpdate,
} from "@/modules/curator/questions/presentation";
import type { QuestionVisibility, StaffQuestion } from "@/modules/curator/questions/types";
import { getCourse, getStep } from "@/modules/student/courses/api";
import { documentTitle, stepDocument, stepLabels } from "@/modules/student/courses/presentation";
import type { Course, StudentStep } from "@/modules/student/courses/types";

const questions = ref<StaffQuestion[]>([]);
const filter = ref<"unanswered" | "all">("unanswered");
const selectedId = ref<number | null>(null);
const answer = ref("");
const visibility = ref<QuestionVisibility>("private");
const taskOpen = ref(false);
const steps = ref(new Map<number, StudentStep>());
const stepNumbers = ref(new Map<number, string>());
const loadingSteps = ref(new Set<number>());
const stepErrors = ref(new Map<number, string>());
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const saved = ref("");
let loadVersion = 0;

const unansweredCount = computed(
  () => questions.value.filter((item) => item.answer === null).length,
);
const visibleQuestions = computed(() =>
  filter.value === "all" ? questions.value : questions.value.filter((item) => item.answer === null),
);
const selected = computed(
  () => questions.value.find((item) => item.id === selectedId.value) ?? null,
);
const similar = computed(() =>
  selected.value
    ? questions.value.filter(
        (item) => item.step_id === selected.value?.step_id && item.id !== selected.value?.id,
      )
    : [],
);
const changes = computed(() =>
  selected.value ? questionUpdate(selected.value, answer.value, visibility.value) : {},
);
const canSave = computed(
  () =>
    Boolean(selected.value?.can_answer) &&
    answer.value.trim().length > 0 &&
    answer.value.length <= 10_000 &&
    Object.keys(changes.value).length > 0 &&
    !saving.value,
);

function taskTitle(stepId: number): string {
  const step = steps.value.get(stepId);
  return step
    ? documentTitle(stepDocument(step.type, step.content), stepLabels[step.type])
    : `Задание #${stepId}`;
}

function stepLabel(question: StaffQuestion): string {
  const number = stepNumbers.value.get(question.step_id);
  const title = steps.value.get(question.step_id);
  return `${number ? `Шаг ${number}` : question.module_title} · ${
    title ? taskTitle(question.step_id) : `задание #${question.step_id}`
  }`;
}

async function loadStep(stepId: number, version: number): Promise<void> {
  if (steps.value.has(stepId) || loadingSteps.value.has(stepId)) return;
  loadingSteps.value = new Set([...loadingSteps.value, stepId]);
  stepErrors.value = new Map(stepErrors.value);
  stepErrors.value.delete(stepId);
  try {
    const step = await getStep(stepId);
    if (version !== loadVersion) return;
    steps.value = new Map(steps.value).set(stepId, step);
  } catch (cause) {
    if (version !== loadVersion) return;
    stepErrors.value = new Map(stepErrors.value).set(stepId, getApiErrorMessage(cause));
  } finally {
    if (version === loadVersion) {
      const next = new Set(loadingSteps.value);
      next.delete(stepId);
      loadingSteps.value = next;
    }
  }
}

async function loadMetadata(items: StaffQuestion[], version: number): Promise<void> {
  const courseIds = [...new Set(items.map((item) => item.course_id))];
  void Promise.allSettled(
    courseIds.map(async (courseId) => {
      const course: Course = await getCourse(courseId);
      if (version !== loadVersion) return;
      const next = new Map(stepNumbers.value);
      course.modules.forEach((module, moduleIndex) =>
        module.steps.forEach((step, stepIndex) =>
          next.set(step.id, `${moduleIndex + 1}.${stepIndex + 1}`),
        ),
      );
      stepNumbers.value = next;
    }),
  );

  const ids = [...new Set(items.map((item) => item.step_id))];
  const activeStepId = items.find((item) => item.id === selectedId.value)?.step_id;
  if (activeStepId !== undefined) {
    ids.splice(ids.indexOf(activeStepId), 1);
    ids.unshift(activeStepId);
  }
  let cursor = 0;
  await Promise.all(
    Array.from({ length: Math.min(4, ids.length) }, async () => {
      while (cursor < ids.length && version === loadVersion) {
        const id = ids[cursor++];
        if (id !== undefined) await loadStep(id, version);
      }
    }),
  );
}

async function load(): Promise<void> {
  const version = ++loadVersion;
  loading.value = true;
  error.value = "";
  saved.value = "";
  steps.value = new Map();
  stepNumbers.value = new Map();
  stepErrors.value = new Map();
  loadingSteps.value = new Set();
  try {
    const items = await questionApi.all();
    if (version !== loadVersion) return;
    questions.value = items;
    selectedId.value = visibleQuestions.value[0]?.id ?? null;
    void loadMetadata(items, version);
  } catch (cause) {
    if (version === loadVersion) error.value = getApiErrorMessage(cause);
  } finally {
    if (version === loadVersion) loading.value = false;
  }
}

function selectFilter(next: "unanswered" | "all"): void {
  saved.value = "";
  filter.value = next;
  if (!visibleQuestions.value.some((item) => item.id === selectedId.value)) {
    selectedId.value = visibleQuestions.value[0]?.id ?? null;
  }
}

function selectQuestion(id: number): void {
  saved.value = "";
  if (!visibleQuestions.value.some((item) => item.id === id)) filter.value = "all";
  selectedId.value = id;
}

function toggleTask(): void {
  taskOpen.value = !taskOpen.value;
  if (taskOpen.value && selected.value) void loadStep(selected.value.step_id, loadVersion);
}

async function save(): Promise<void> {
  const question = selected.value;
  if (!question || !canSave.value) return;
  saving.value = true;
  error.value = "";
  saved.value = "";
  try {
    const updated = await questionApi.update(question.id, changes.value);
    questions.value = questions.value.map((item) => (item.id === updated.id ? updated : item));
    if (selectedId.value === question.id) {
      if (filter.value === "unanswered") {
        selectedId.value = visibleQuestions.value[0]?.id ?? null;
      } else {
        answer.value = updated.answer ?? "";
        visibility.value = updated.visibility;
      }
    }
    saved.value = "Ответ сохранён.";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    saving.value = false;
  }
}

watch(selectedId, (id) => {
  const question = questions.value.find((item) => item.id === id);
  answer.value = question?.answer ?? "";
  visibility.value = question?.visibility ?? "private";
  taskOpen.value = false;
  error.value = "";
});

onMounted(load);
onBeforeUnmount(() => {
  ++loadVersion;
});
</script>

<template>
  <section class="curator-questions" aria-label="Вопросы учеников">
    <aside class="curator-questions__queue" aria-label="Список вопросов">
      <h2>Вопросы</h2>
      <div class="curator-questions__tabs" role="group" aria-label="Фильтр вопросов">
        <button
          type="button"
          :class="{ 'curator-questions__tab--active': filter === 'unanswered' }"
          :aria-pressed="filter === 'unanswered'"
          @click="selectFilter('unanswered')"
        >
          Без ответа · {{ unansweredCount }}
        </button>
        <button
          type="button"
          :class="{ 'curator-questions__tab--active': filter === 'all' }"
          :aria-pressed="filter === 'all'"
          @click="selectFilter('all')"
        >
          Все
        </button>
      </div>
      <div v-if="loading" class="curator-questions__queue-state" role="status">
        Загружаем вопросы…
      </div>
      <div v-else-if="!visibleQuestions.length" class="curator-questions__queue-state">
        {{ filter === "unanswered" ? "Вопросов без ответа нет." : "Вопросов пока нет." }}
      </div>
      <nav v-else class="curator-questions__items" aria-label="Вопросы">
        <button
          v-for="question in visibleQuestions"
          :key="question.id"
          class="curator-questions__item"
          :class="{ 'curator-questions__item--selected': question.id === selectedId }"
          type="button"
          :aria-pressed="question.id === selectedId"
          @click="selectQuestion(question.id)"
        >
          <span class="curator-questions__item-head">
            <b>{{ questionAuthor(question) }}</b>
            <time :datetime="question.created_at">{{ questionAge(question) }}</time>
          </span>
          <small>{{ stepLabel(question) }}</small>
          <span class="curator-questions__item-text">{{ question.text }}</span>
          <span v-if="question.answer !== null" class="curator-questions__answered">С ответом</span>
          <span v-if="!question.can_answer" class="curator-questions__readonly">Только чтение</span>
        </button>
      </nav>
    </aside>

    <div class="curator-questions__main">
      <div v-if="error" class="curator-questions__error" role="alert">
        {{ error }}
        <button v-if="!questions.length" type="button" @click="load">Повторить</button>
      </div>
      <p v-if="saved" class="curator-questions__success" role="status">{{ saved }}</p>
      <div v-if="!selected && !loading" class="curator-questions__empty">
        {{ filter === "unanswered" ? "Все вопросы получили ответ." : "Выберите вопрос из списка." }}
      </div>
      <template v-else-if="selected">
        <div class="curator-questions__breadcrumb">
          {{ selected.course_title }} · {{ stepLabel(selected) }}
        </div>
        <section class="curator-questions__task">
          <button
            class="curator-questions__task-toggle"
            type="button"
            :aria-expanded="taskOpen"
            :aria-controls="`question-task-${selected.id}`"
            @click="toggleTask"
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
          <div v-if="taskOpen" :id="`question-task-${selected.id}`">
            <QuestionTask v-if="steps.get(selected.step_id)" :step="steps.get(selected.step_id)!" />
            <div v-else class="curator-questions__task-state">
              <template v-if="loadingSteps.has(selected.step_id)">Загружаем задание…</template>
              <template v-else>{{
                stepErrors.get(selected.step_id) || "Задание пока недоступно."
              }}</template>
              <button
                v-if="!loadingSteps.has(selected.step_id)"
                type="button"
                @click="loadStep(selected.step_id, loadVersion)"
              >
                Повторить
              </button>
            </div>
          </div>
        </section>

        <section class="curator-questions__card curator-questions__question">
          <div>
            <b>{{ questionAuthor(selected) }}</b> <span>· {{ questionAge(selected) }} назад</span>
          </div>
          <p>{{ selected.text }}</p>
        </section>

        <section v-if="similar.length" class="curator-questions__card curator-questions__similar">
          <b>Похожие вопросы на этом шаге</b>
          <div v-for="item in similar.slice(0, 3)" :key="item.id">
            <button type="button" @click="selectQuestion(item.id)">
              {{ questionAuthor(item) }}: «{{ item.text }}»
            </button>
          </div>
        </section>

        <label class="curator-questions__answer-label" for="curator-question-answer">Ответ</label>
        <textarea
          id="curator-question-answer"
          v-model="answer"
          class="curator-questions__answer"
          rows="4"
          maxlength="10000"
          :readonly="!selected.can_answer"
          placeholder="Напишите ответ ученику…"
        />
        <div class="curator-questions__visibility">
          <button
            class="curator-questions__switch"
            :class="{ 'curator-questions__switch--on': visibility === 'course' }"
            type="button"
            role="switch"
            :aria-checked="visibility === 'course'"
            aria-label="Показать ответ всем на этом шаге"
            :disabled="!selected.can_answer"
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
        <p v-if="!selected.can_answer" class="curator-questions__notice">
          Это публичный вопрос другой группы. Ответ можно только прочитать.
        </p>
        <div v-else class="curator-questions__actions">
          <button type="button" :disabled="!canSave" @click="save">
            {{
              saving
                ? "Сохраняем…"
                : selected.answer === null
                  ? "Опубликовать ответ"
                  : "Сохранить изменения"
            }}
          </button>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.curator-questions {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  background: var(--color-bg);
  font-size: 14px;
  line-height: 1.5;
}
.curator-questions__queue {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  padding: 24px 14px;
  border-right: 1px solid var(--color-border);
}
.curator-questions__queue h2 {
  margin: 0 0 4px;
  font-size: 28px;
  line-height: 1.2;
}
.curator-questions__tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 4px;
}
.curator-questions__tabs button {
  padding: 4px 10px;
  border: 0;
  border-radius: 999px;
  background: #fff;
  color: var(--color-muted);
  font: 600 13px var(--font-sans);
  white-space: nowrap;
  cursor: pointer;
}
.curator-questions__tabs .curator-questions__tab--active {
  background: var(--color-text);
  color: #fff;
}
.curator-questions__items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
  padding: 2px;
}
.curator-questions__queue-state {
  padding: 16px 10px;
  color: var(--color-muted);
}
.curator-questions__item {
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
.curator-questions__item:hover {
  border-color: var(--color-primary-pale);
}
.curator-questions__item--selected,
.curator-questions__item--selected:hover {
  border: 2px solid var(--color-primary);
  padding: 9px 11px;
  background: var(--color-primary-soft);
}
.curator-questions__item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.curator-questions__item-head time,
.curator-questions__item small {
  color: var(--color-muted);
  font-size: 12px;
}
.curator-questions__item-text {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}
.curator-questions__answered,
.curator-questions__readonly {
  width: max-content;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--color-success-soft);
  color: var(--color-success);
  font-size: 12px;
  font-weight: 600;
}
.curator-questions__readonly {
  background: var(--color-neutral-soft);
  color: var(--color-neutral);
}
.curator-questions__main {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 24px;
}
.curator-questions__main > * {
  box-sizing: border-box;
  width: 100%;
  max-width: 860px;
}
.curator-questions__breadcrumb {
  color: var(--color-muted);
}
.curator-questions__card,
.curator-questions__task,
.curator-questions__visibility {
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: #fff;
}
.curator-questions__card {
  padding: 14px 16px;
}
.curator-questions__question span {
  color: var(--color-muted);
}
.curator-questions__question p {
  margin: 4px 0 0;
  font-size: 15px;
  white-space: pre-wrap;
}
.curator-questions__task {
  overflow: hidden;
}
.curator-questions__task-toggle {
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
.curator-questions__task-toggle svg {
  width: 20px;
  height: 20px;
  transition: transform 0.15s;
}
.curator-questions__task-toggle[aria-expanded="true"] svg {
  transform: rotate(180deg);
}
.curator-questions__task-state {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--color-border);
  color: var(--color-muted);
}
.curator-questions__task-state button,
.curator-questions__error button {
  border: 0;
  background: none;
  color: var(--color-primary);
  font: inherit;
  cursor: pointer;
}
.curator-questions__similar {
  display: grid;
  gap: 4px;
  border-style: dashed;
  background: var(--color-bg);
}
.curator-questions__similar button {
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-text);
  text-align: left;
  font: inherit;
  cursor: pointer;
}
.curator-questions__similar button:hover {
  color: var(--color-primary);
}
.curator-questions__answer-label {
  font-weight: 600;
}
.curator-questions__answer {
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
.curator-questions__visibility {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
}
.curator-questions__visibility p {
  margin: 3px 0 0;
  color: var(--color-muted);
  font-size: 13px;
}
.curator-questions__switch {
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
.curator-questions__switch::after {
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
.curator-questions__switch--on {
  background: var(--color-primary);
}
.curator-questions__switch--on::after {
  left: 19px;
}
.curator-questions__switch:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.curator-questions__actions {
  display: flex;
  justify-content: flex-end;
}
.curator-questions__actions button {
  min-height: 40px;
  padding: 0 16px;
  border: 0;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font: 600 14px var(--font-sans);
  cursor: pointer;
}
.curator-questions__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.curator-questions__error,
.curator-questions__success,
.curator-questions__notice {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
}
.curator-questions__error {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.curator-questions__success {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.curator-questions__notice {
  background: var(--color-neutral-soft);
  color: var(--color-muted);
}
.curator-questions__empty {
  color: var(--color-muted);
}
@media (max-width: 760px) {
  .curator-questions {
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: 100%;
  }
  .curator-questions__queue {
    max-height: 320px;
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }
  .curator-questions__main {
    overflow: visible;
    padding: 20px 16px 36px;
  }
}
</style>
