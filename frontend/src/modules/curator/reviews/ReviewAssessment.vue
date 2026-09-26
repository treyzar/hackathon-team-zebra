<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { getApiErrorMessage } from "@/api/errors";
import { reviewApi } from "./api";
import {
  checklistScore,
  checklistVerdict,
  type GradeMode,
  reviewChecklist,
  verdictFor,
} from "./presentation";
import type { ReviewDetail } from "./types";

const props = defineProps<{ detail: ReviewDetail }>();
const emit = defineEmits<{ saved: [id: number] }>();
const mode = ref<GradeMode>("full");
const score = ref(0);
const comment = ref("");
const saving = ref(false);
const error = ref("");
// With a checklist the curator marks met criteria and the score follows.
const checklist = computed(() => reviewChecklist(props.detail));
const checked = ref<string[]>([]);
const checklistTotal = computed(() => checklistScore(checklist.value, checked.value));

watch(
  () => props.detail.id,
  () => {
    const autoScore = props.detail.auto_score;
    mode.value = "full";
    score.value = autoScore ?? Math.max(0, Math.floor(props.detail.max_score / 2));
    comment.value = "";
    error.value = "";
    checked.value = [];
  },
  { immediate: true },
);

async function save(): Promise<void> {
  if (saving.value) return;
  if (
    !checklist.value.length &&
    mode.value === "partial" &&
    (!Number.isFinite(score.value) || score.value < 0 || score.value > props.detail.max_score)
  ) {
    error.value = `Укажите от 0 до ${props.detail.max_score} баллов.`;
    return;
  }
  saving.value = true;
  error.value = "";
  try {
    await reviewApi.save(
      props.detail.id,
      checklist.value.length
        ? checklistVerdict(
            mode.value !== "revise",
            checklist.value.filter((item) => checked.value.includes(item.id)).map((i) => i.id),
            comment.value,
          )
        : verdictFor(mode.value, score.value, props.detail.max_score, comment.value),
    );
    emit("saved", props.detail.id);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <form class="review-assessment" aria-label="Оценка работы" @submit.prevent="save">
    <h2>Оценка</h2>
    <template v-if="checklist.length">
      <div class="review-assessment__eyebrow">ЧЕК-ЛИСТ</div>
      <label v-for="item in checklist" :key="item.id" class="review-assessment__criterion">
        <input v-model="checked" type="checkbox" :value="item.id" />
        <span>
          <b>{{ item.text }}</b>
          <small v-if="item.hint">{{ item.hint }}</small>
        </span>
        <em>+{{ item.points }}</em>
      </label>
      <p class="review-assessment__total">
        Итого: <b>{{ checklistTotal }}</b> из {{ detail.max_score }}
      </p>
      <div class="review-assessment__eyebrow">РЕШЕНИЕ</div>
      <label
        class="review-assessment__choice"
        :class="{ 'review-assessment__choice--active': mode !== 'revise' }"
      >
        <input v-model="mode" type="radio" value="full" name="grade-mode" />
        <span>
          <b>Зачесть</b>
          <small>{{ checklistTotal }} из {{ detail.max_score }} баллов по чек-листу</small>
        </span>
      </label>
      <label
        class="review-assessment__choice"
        :class="{ 'review-assessment__choice--active': mode === 'revise' }"
      >
        <input v-model="mode" type="radio" value="revise" name="grade-mode" />
        <span>
          <b>Вернуть на доработку</b>
          <small>Баллы по чек-листу, ученик может пересдать</small>
        </span>
      </label>
    </template>

    <template v-else>
      <div class="review-assessment__eyebrow">РЕШЕНИЕ</div>

      <label
        class="review-assessment__choice"
        :class="{ 'review-assessment__choice--active': mode === 'full' }"
      >
        <input v-model="mode" type="radio" value="full" name="grade-mode" />
        <span>
          <b>Зачесть полностью</b>
          <small>{{ detail.max_score }} из {{ detail.max_score }} баллов</small>
        </span>
      </label>

      <div
        class="review-assessment__choice review-assessment__choice--partial"
        :class="{ 'review-assessment__choice--active': mode === 'partial' }"
      >
        <label class="review-assessment__partial-head">
          <input v-model="mode" type="radio" value="partial" name="grade-mode" />
          <b>Зачесть частично</b>
        </label>
        <div class="review-assessment__score">
          <input
            v-model.number="score"
            type="number"
            min="0"
            :max="detail.max_score"
            step="any"
            aria-label="Баллы за работу"
            @focus="mode = 'partial'"
          />
          <span>из {{ detail.max_score }}</span>
        </div>
        <input
          v-model.number="score"
          type="range"
          min="0"
          :max="detail.max_score"
          step="1"
          aria-label="Выбрать баллы"
          @input="mode = 'partial'"
        />
      </div>

      <label
        class="review-assessment__choice"
        :class="{ 'review-assessment__choice--active': mode === 'revise' }"
      >
        <input v-model="mode" type="radio" value="revise" name="grade-mode" />
        <span>
          <b>Вернуть на доработку</b>
          <small>Баллы не начисляются, ученик пересдаёт</small>
        </span>
      </label>
    </template>

    <label for="review-comment" class="review-assessment__comment-label">Комментарий ученику</label>
    <textarea
      id="review-comment"
      v-model="comment"
      rows="4"
      maxlength="10000"
      placeholder="Оставьте комментарий к работе"
    />
    <p v-if="error" class="review-assessment__error" role="alert">{{ error }}</p>
    <div class="review-assessment__spacer" />
    <button type="submit" :disabled="saving">{{ saving ? "Сохраняем…" : "Сохранить" }}</button>
  </form>
</template>

<style scoped>
.review-assessment {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  min-height: 0;
  height: 100%;
  padding: 18px;
  border-left: 1px solid var(--color-border);
  background: #fff;
  font-size: 14px;
  line-height: 1.5;
}
.review-assessment h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.review-assessment__eyebrow {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.review-assessment__choice {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
}
.review-assessment__choice--active {
  border: 2px solid var(--color-primary);
  background: var(--color-primary-soft);
}
.review-assessment__choice input[type="radio"] {
  width: 17px;
  height: 17px;
  flex: none;
  margin: 2px 0 0;
  accent-color: var(--color-primary);
}
.review-assessment__choice span,
.review-assessment__partial-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.review-assessment__choice small {
  color: var(--color-muted);
  font-size: 12px;
}
.review-assessment__choice--partial {
  flex-direction: column;
  gap: 8px;
}
.review-assessment__partial-head {
  flex-direction: row;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}
.review-assessment__score {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 27px;
}
.review-assessment__score input {
  width: 54px;
  height: 32px;
  box-sizing: border-box;
  border: 1px solid var(--color-primary-pale);
  border-radius: 8px;
  text-align: center;
  font: 700 15px var(--font-sans);
}
.review-assessment__choice input[type="range"] {
  width: 100%;
  margin: 0;
  accent-color: var(--color-primary);
}
.review-assessment__criterion {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  cursor: pointer;
}
.review-assessment__criterion input {
  margin-top: 3px;
}
.review-assessment__criterion span {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.review-assessment__criterion small {
  color: #68748a;
}
.review-assessment__criterion em {
  color: #17915a;
  font-style: normal;
  font-weight: 700;
}
.review-assessment__total {
  margin: 0;
}
.review-assessment__comment-label {
  margin-top: 2px;
  font-weight: 600;
}
.review-assessment textarea {
  height: 84px;
  min-height: 84px;
  box-sizing: border-box;
  padding: 10px;
  overflow-y: auto;
  resize: none;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font: 14px/1.5 var(--font-sans);
}
.review-assessment__error {
  margin: 0;
  color: var(--color-danger);
  font-size: 13px;
}
.review-assessment__spacer {
  flex: 1;
}
.review-assessment button {
  height: 44px;
  flex: none;
  border: 0;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font: 600 15px var(--font-sans);
  cursor: pointer;
}
.review-assessment button:disabled {
  opacity: 0.6;
  cursor: wait;
}
</style>
