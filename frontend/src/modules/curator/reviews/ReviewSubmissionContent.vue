<script setup lang="ts">
import { computed } from "vue";

import RichContent from "@/modules/student/courses/RichContent.vue";
import { formatDate, stepTypeLabels } from "@/modules/admin/shared/format";
import ReviewFiles from "./ReviewFiles.vue";
import {
  answerFiles,
  attemptNumber,
  plainText,
  referenceChoices,
  referenceDocument,
  referenceText,
  stepNumber,
  studentInitials,
  studentLabel,
  submittedChoices,
  taskBody,
  taskDocument,
  taskTitle,
} from "./presentation";
import type { ReviewDetail } from "./types";

const props = defineProps<{ detail: ReviewDetail }>();
const question = computed(() => taskBody(taskDocument(props.detail.content)));
const reference = computed(() => referenceDocument(props.detail.answer_key));
const files = computed(() => answerFiles(props.detail.answer));
const referenceFiles = computed(() => answerFiles(props.detail.answer_key));
const choices = computed(() => submittedChoices(props.detail));
const correctChoices = computed(() => referenceChoices(props.detail));
const answerText = computed(() => plainText(props.detail.answer.text ?? props.detail.answer.value));
const code = computed(() => plainText(props.detail.answer.code));
const solution = computed(() => referenceText(props.detail));
const criteria = computed(() => plainText(props.detail.answer_key.criteria));
const samples = computed(() =>
  Array.isArray(props.detail.content.samples) ? props.detail.content.samples : [],
);
const groups = computed(() =>
  Array.isArray(props.detail.result_details.groups) ? props.detail.result_details.groups : [],
);
const answerLink = computed(() =>
  /^https?:\/\/\S+$/i.test(answerText.value) ? answerText.value : null,
);
</script>

<template>
  <div class="review-material" role="region" aria-label="Задание и работа ученика" tabindex="0">
    <div class="review-material__breadcrumb">
      {{ detail.course_title }} · {{ detail.module_title }} · шаг {{ stepNumber(detail) }} ·
      {{ stepTypeLabels[detail.step_type] }}
    </div>
    <h2>{{ taskTitle(detail.content, detail.step_id) }}</h2>
    <div class="review-material__student">
      <span class="review-material__avatar" aria-hidden="true">{{ studentInitials(detail) }}</span>
      <strong>{{ studentLabel(detail) }}</strong>
      <span v-if="detail.is_late" class="review-material__late">После дедлайна</span>
      <span v-if="detail.is_outdated" class="review-material__late">Старая редакция</span>
    </div>

    <section class="review-material__card" aria-labelledby="review-task-heading">
      <h3 id="review-task-heading">Задание</h3>
      <RichContent v-if="question" :document="question" />
      <p v-else class="review-material__muted">Описание задания не заполнено.</p>
      <div v-if="samples.length" class="review-material__samples">
        <div v-for="(sample, index) in samples" :key="index">
          <b>Пример {{ index + 1 }}</b>
          <pre>
Ввод: {{ (sample as { input?: string }).input ?? "" }}
Вывод: {{ (sample as { output?: string }).output ?? "" }}</pre>
        </div>
      </div>
    </section>

    <section
      class="review-material__card review-material__card--student"
      aria-labelledby="review-work-heading"
    >
      <div class="review-material__card-heading">
        <h3 id="review-work-heading">Работа ученика</h3>
        <span>попытка {{ attemptNumber(detail) }} · {{ formatDate(detail.created_at) }}</span>
      </div>
      <pre v-if="code" class="review-material__code">{{ code }}</pre>
      <p v-if="answerText" class="review-material__answer">{{ answerText }}</p>
      <a v-if="answerLink" :href="answerLink" target="_blank" rel="noopener noreferrer"
        >Открыть ссылку ↗</a
      >
      <ul v-if="choices.length" class="review-material__options">
        <li v-for="(choice, index) in choices" :key="index">{{ choice }}</li>
      </ul>
      <ReviewFiles :ids="files" label="Файл ученика" />
      <p v-if="detail.auto_score !== null" class="review-material__muted">
        Балл после тестов: {{ detail.auto_score }} из {{ detail.max_score }}
      </p>
      <div v-if="groups.length" class="review-material__groups">
        <b>Результаты групп тестов</b>
        <div v-for="(group, index) in groups" :key="index">
          {{ (group as { name?: string }).name || `Группа ${index + 1}` }} ·
          {{ (group as { passed?: boolean }).passed ? "пройдена" : "не пройдена" }}
        </div>
      </div>
      <p
        v-if="!code && !answerText && !choices.length && !files.length"
        class="review-material__muted"
      >
        В работе нет текстового ответа или файлов.
      </p>
    </section>

    <section
      class="review-material__card review-material__card--reference"
      aria-labelledby="review-reference-heading"
    >
      <div class="review-material__card-heading">
        <h3 id="review-reference-heading">Эталонное решение</h3>
        <span class="review-material__reference-badge">видит только куратор</span>
      </div>
      <RichContent v-if="reference" :document="reference" />
      <pre
        v-else-if="detail.step_type === 'programming' && solution"
        class="review-material__code"
        >{{ solution }}</pre>
      <p v-else-if="solution" class="review-material__answer">{{ solution }}</p>
      <ul v-if="correctChoices.length" class="review-material__options">
        <li v-for="(choice, index) in correctChoices" :key="index">{{ choice }}</li>
      </ul>
      <ReviewFiles :ids="referenceFiles" label="Эталонный файл" />
      <div v-if="criteria" class="review-material__criteria"><b>Критерии:</b> {{ criteria }}</div>
      <p
        v-if="
          !reference && !solution && !correctChoices.length && !referenceFiles.length && !criteria
        "
        class="review-material__muted"
      >
        Эталонное решение не добавлено.
      </p>
    </section>
  </div>
</template>

<style scoped>
.review-material {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 20px 24px 32px;
  font-size: 14px;
  line-height: 1.5;
}
.review-material__breadcrumb,
.review-material__muted,
.review-material__card-heading > span {
  color: var(--color-muted);
}
.review-material h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
}
.review-material__student,
.review-material__card-heading {
  display: flex;
  align-items: center;
  gap: 8px;
}
.review-material__avatar {
  display: grid;
  width: 28px;
  height: 28px;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
}
.review-material__late {
  color: var(--color-warning);
  font-size: 12px;
  font-weight: 700;
}
.review-material__card {
  min-width: 0;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: #fff;
  overflow-wrap: anywhere;
}
.review-material__card h3 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
}
.review-material__card-heading {
  justify-content: space-between;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.review-material__card-heading h3 {
  margin: 0;
}
.review-material__card-heading > span {
  font-size: 12px;
}
.review-material__card--student {
  border: 2px solid var(--color-primary-pale);
}
.review-material__card--reference {
  border: 2px dashed var(--color-success);
}
.review-material__reference-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-success-soft);
  color: var(--color-success) !important;
  font-weight: 600;
}
.review-material__card p {
  margin: 8px 0;
}
.review-material__code,
.review-material__samples pre {
  max-width: 100%;
  overflow-x: auto;
  padding: 14px;
  border-radius: 12px;
  background: var(--color-neutral-soft);
  font: 13px/1.5 var(--font-mono);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.review-material__options {
  margin: 8px 0;
  padding-left: 20px;
}
.review-material__criteria,
.review-material__groups {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: var(--color-bg);
}
.review-material a {
  color: var(--color-primary);
  font-weight: 600;
}
</style>
