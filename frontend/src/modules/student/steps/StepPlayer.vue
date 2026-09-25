<script setup lang="ts">
import { computed, toRef } from "vue";
import { RouterLink, type RouteLocationRaw } from "vue-router";
import {
  blockReason,
  pointsText,
  pointsWord,
  stepLabels,
} from "@/modules/student/courses/presentation";
import RichContent from "@/modules/student/courses/RichContent.vue";
import type { StudentStep } from "@/modules/student/courses/types";
import StepAnswerForm from "./StepAnswerForm.vue";
import StepAnswerReveal from "./StepAnswerReveal.vue";
import StepResult from "./StepResult.vue";
import { useStepPlayer } from "./useStepPlayer";
import "./step-player.css";

const props = defineProps<{
  step: StudentStep;
  number: string;
  /** Where "Следующий шаг" leads; null on the last or a still locked step. */
  next?: RouteLocationRaw | null;
}>();
const emit = defineEmits<{ refresh: [] }>();

const {
  title,
  bodyDocument,
  choice,
  freeText,
  programming,
  selected,
  answerText,
  code,
  files,
  revealed,
  loading,
  saving,
  error,
  latest,
  blocked,
  remaining,
  correctChoices,
  referenceSolution,
  referenceDocument,
  toggleOption,
  addFiles,
  removeFile,
  submit,
  revealAnswer,
} = useStepPlayer({
  step: toRef(props, "step"),
  onRefresh: () => emit("refresh"),
});

const passed = computed(
  () =>
    props.step.progress.state === "passed" ||
    latest.value?.status === "correct" ||
    latest.value?.status === "accepted",
);
const onReview = computed(() => !passed.value && latest.value?.status === "pending_review");
// A passed or handed-in step lets the student move on; resubmitting becomes secondary.
const canMoveOn = computed(() => Boolean(props.next) && (passed.value || onReview.value));
const earned = computed(() => latest.value?.score ?? props.step.progress.earned);
</script>

<template>
  <article class="student-lesson">
    <div class="student-lesson-top">
      <span class="student-lesson-meta">
        {{ stepLabels[step.type] }} · шаг {{ number }}
        <span v-if="step.deadline">
          · до {{ new Date(step.deadline.due_at).toLocaleDateString("ru-RU") }}
        </span>
      </span>
      <span v-if="passed" class="student-status student-status--passed">
        ✓ Зачтено<template v-if="earned"> · +{{ earned }} {{ pointsWord(earned) }}</template>
      </span>
      <span v-else-if="onReview" class="student-status student-status--review">◷ На проверке</span>
      <span v-else-if="step.max_score" class="student-status">{{
        pointsText(step.max_score)
      }}</span>
      <RouterLink
        v-if="next"
        class="student-next-round"
        :class="{ 'student-next-round--ready': passed || onReview }"
        :to="next"
        aria-label="Следующий шаг"
        title="Следующий шаг"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
      </RouterLink>
    </div>

    <h2>{{ title }}</h2>

    <div v-if="remaining !== null || step.progress.from_previous_version" class="student-lesson-details">
      <span v-if="remaining !== null">{{ remaining }} попыток осталось</span>
      <span v-if="step.progress.from_previous_version"> Результат предыдущей версии учтён </span>
    </div>

    <section v-if="bodyDocument?.content?.length" class="student-paper">
      <RichContent :document="bodyDocument" />
    </section>

    <section v-if="loading" class="student-paper student-muted" role="status">
      Загружаем историю решений…
    </section>

    <section v-else class="student-answer-card">
      <h3>{{ step.type === "theory" ? "Готовы двигаться дальше?" : "Ваш ответ" }}</h3>

      <StepAnswerForm
        :step="step"
        :choice="choice"
        :free-text="freeText"
        :programming="programming"
        :selected="selected"
        :answer-text="answerText"
        :code="code"
        :files="files"
        :correct-choices="correctChoices"
        :blocked="blocked"
        @toggle-option="toggleOption"
        @add-files="addFiles"
        @remove-file="removeFile"
        @update:answer-text="answerText = $event"
        @update:code="code = $event"
      />

      <div v-if="error" class="student-alert student-alert--error" role="alert">
        {{ error }}
      </div>

      <div class="student-submit-row">
        <RouterLink v-if="canMoveOn && next" class="student-submit-button" :to="next"
          >Следующий шаг <span aria-hidden="true">→</span></RouterLink
        >
        <button
          v-if="step.can_submit"
          class="student-submit-button"
          :class="{ 'student-submit-button--secondary': canMoveOn }"
          type="button"
          :disabled="blocked"
          @click="submit"
        >
          {{
            saving
              ? "Отправляем…"
              : step.type === "theory"
                ? "Отметить прочитанным"
                : latest
                  ? "Отправить снова"
                  : "Отправить на проверку"
          }}
        </button>

        <p v-else-if="!canMoveOn" class="student-muted">
          {{ blockReason(step.submit_block_reason) }}
        </p>
      </div>
    </section>

    <StepResult v-if="latest" :submission="latest" :max-score="step.max_score" />

    <StepAnswerReveal
      v-if="step.answer_available"
      :choice="choice"
      :revealed="revealed"
      :correct-choices="correctChoices"
      :reference-document="referenceDocument"
      :reference-solution="referenceSolution"
      @reveal="revealAnswer"
    />
  </article>
</template>
