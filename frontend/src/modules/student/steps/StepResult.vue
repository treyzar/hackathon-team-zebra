<script setup lang="ts">
import { computed } from "vue";
import { pointsWord } from "@/modules/student/courses/presentation";
import type { Submission } from "@/modules/student/courses/types";
import {
  failedTests,
  groupStatus,
  resultStatus,
  sampleResults,
  testGroups,
  verdictLabel,
} from "./result-presentation";

const props = defineProps<{
  submission: Submission;
  maxScore: number;
}>();

const samples = computed(() => sampleResults(props.submission.result_details));
const groups = computed(() => testGroups(props.submission.result_details));
</script>

<template>
  <section
    class="student-result"
    :class="`student-result--${submission.status}`"
    aria-live="polite"
  >
    <div class="student-result-head">
      <strong>{{ resultStatus(submission.status, submission.result_details) }}</strong>
      <span v-if="submission.score !== null">
        {{ submission.score }} / {{ maxScore }} {{ pointsWord(maxScore) }}
      </span>
    </div>

    <p v-if="submission.review_comment">{{ submission.review_comment }}</p>
    <p v-if="submission.is_late" class="student-muted">Решение отправлено после срока.</p>

    <div v-if="samples.length" class="student-test-results">
      <h4>Примеры</h4>
      <div v-for="(sample, index) in samples" :key="index" class="student-test-row">
        <strong>Пример {{ index + 1 }} · {{ verdictLabel(sample.verdict) }}</strong>
        <div v-if="sample.expected != null">
          <span>Ожидаемый вывод:</span>
          <pre>{{ sample.expected }}</pre>
        </div>
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

    <div v-if="groups.length" class="student-test-results">
      <h4>Скрытые тесты</h4>
      <div v-for="(group, index) in groups" :key="index" class="student-group-result">
        <div class="student-group-result__summary">
          <span>{{ group.name || `Группа ${index + 1}` }} · {{ groupStatus(group) }}</span>
          <strong v-if="group.points != null">{{ group.earned ?? 0 }} / {{ group.points }}</strong>
        </div>
        <ul v-if="failedTests(group).length" class="student-group-result__tests">
          <li v-for="test in failedTests(group)" :key="test.number">
            Тест {{ test.number }} · {{ test.verdict }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
