<script setup lang="ts">
import { computed } from "vue";
import { submissionLabel } from "@/modules/student/courses/presentation";
import type { Submission } from "@/modules/student/courses/types";

const props = defineProps<{
  submission: Submission;
  maxScore: number;
}>();

const sampleResults = computed(() => {
  const value = props.submission.result_details.samples;
  return Array.isArray(value)
    ? (value as {
        stdout?: string;
        stderr?: string;
        verdict?: string;
      }[])
    : [];
});

const testGroups = computed(() => {
  const value = props.submission.result_details.groups;
  return Array.isArray(value)
    ? (value as {
        name?: string;
        passed?: boolean;
        earned?: number;
        points?: number;
      }[])
    : [];
});
</script>

<template>
  <section
    class="student-result"
    :class="`student-result--${submission.status}`"
    aria-live="polite"
  >
    <div class="student-result-head">
      <strong>{{ submissionLabel(submission.status) }}</strong>
      <span v-if="submission.score !== null"> {{ submission.score }} / {{ maxScore }} баллов </span>
    </div>

    <p v-if="submission.review_comment">{{ submission.review_comment }}</p>
    <p v-if="submission.is_late" class="student-muted">Решение отправлено после срока.</p>

    <div v-if="sampleResults.length" class="student-test-results">
      <h4>Примеры</h4>
      <div v-for="(sample, index) in sampleResults" :key="index" class="student-test-row">
        <strong>
          Пример {{ index + 1 }} · {{ sample.verdict === "ok" ? "верно" : sample.verdict }}
        </strong>
        <div v-if="sample.stdout != null">
          <span>Вывод программы:</span>
          <pre>{{ sample.stdout }}</pre>
        </div>
        <div v-if="sample.stderr">
          <span>Ошибки:</span>
          <pre>{{ sample.stderr }}</pre>
        </div>
      </div>
    </div>

    <div v-if="testGroups.length" class="student-test-results">
      <h4>Скрытые тесты</h4>
      <div v-for="(group, index) in testGroups" :key="index" class="student-group-result">
        <span>
          {{ group.name || `Группа ${index + 1}` }} ·
          {{ group.passed ? "пройдена" : "не пройдена" }}
        </span>
        <strong v-if="group.points != null">{{ group.earned ?? 0 }} / {{ group.points }}</strong>
      </div>
    </div>
  </section>
</template>
