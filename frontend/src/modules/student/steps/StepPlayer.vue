<script setup lang="ts">
import { toRef } from "vue";
import { blockReason, stepLabels } from "@/modules/student/courses/presentation";
import RichContent from "@/modules/student/courses/RichContent.vue";
import type { StudentStep } from "@/modules/student/courses/types";
import StepAnswerForm from "./StepAnswerForm.vue";
import StepAnswerReveal from "./StepAnswerReveal.vue";
import StepResult from "./StepResult.vue";
import { useStepPlayer } from "./useStepPlayer";
import "./step-player.css";

const props = defineProps<{ step: StudentStep; number: string }>();
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
</script>

<template>
  <article class="student-lesson">
    <div class="student-lesson-meta">
      {{ stepLabels[step.type] }} · шаг {{ number }}
      <span v-if="step.deadline">
        · до {{ new Date(step.deadline.due_at).toLocaleDateString("ru-RU") }}
      </span>
    </div>

    <h2>{{ title }}</h2>

    <div class="student-lesson-details">
      <span v-if="step.max_score">
        {{ step.max_score }} балл{{ step.max_score === 1 ? "" : "ов" }}
      </span>
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
        <button
          v-if="step.can_submit"
          class="student-submit-button"
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

        <p v-else class="student-muted">{{ blockReason(step.submit_block_reason) }}</p>
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
