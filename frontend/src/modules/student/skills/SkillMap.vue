<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { errorMessage } from "@/modules/student/courses/presentation";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";
import { skillsApi } from "./api";
import {
  HEX,
  hexLayout,
  initialSkill,
  skillAbout,
  skillCountsText,
  skillIcons,
  skillSegments,
  skillSub,
} from "./presentation";
import type { CourseSkills } from "./types";

const courses = ref<CourseSkills[]>([]);
const loading = ref(true);
const error = ref("");
const selectedKey = ref<string | null>(null);

const layout = computed(() => hexLayout(courses.value));
const selected = computed(() => layout.value.cells.find((cell) => cell.key === selectedKey.value));
const selectedCourse = computed(() =>
  courses.value.find((course) => course.course_id === selected.value?.courseId),
);
// "You are here" marks the first skill of the module with the next step.
const here = computed(() => layout.value.cells.find((cell) => cell.skill?.current));

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    courses.value = await skillsApi.map();
    const first = initialSkill(courses.value);
    selectedKey.value = first ? `${first.courseId}-${first.index}` : null;
  } catch (cause) {
    error.value = errorMessage(cause);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="hexmap" aria-label="Карта навыков">
    <div class="hexmap-head">
      <h2>Карта навыков</h2>
      <span>Каждая сота — навык. Освоил — соседние соты открываются.</span>
    </div>

    <p v-if="loading" class="hexmap-state" role="status">Загружаем карту…</p>
    <p v-else-if="error" class="hexmap-state hexmap-state--error" role="alert">
      {{ error }} <button type="button" @click="load">Повторить</button>
    </p>
    <p v-else-if="!courses.length" class="hexmap-state">
      Вы пока не записаны ни на один курс — здесь появятся его навыки.
    </p>

    <div v-else class="hexmap-body">
      <div class="hexmap-board-wrap">
        <div
          class="hexmap-board"
          :style="{ width: `${layout.width}px`, height: `${layout.height}px` }"
        >
          <span
            v-for="label in layout.labels"
            :key="label.text + label.x"
            class="hexmap-label"
            :class="{ 'hexmap-label--soon': label.soon }"
            :style="{ left: `${label.x}px`, top: `${label.y}px` }"
            >{{ label.text }}</span
          >
          <button
            v-for="cell in layout.cells"
            :key="cell.key"
            type="button"
            class="hx"
            :class="[
              cell.skill ? `hx--${cell.skill.state}` : 'hx--soon',
              { 'hx--current': cell.skill?.current, 'hx--selected': cell.key === selectedKey },
            ]"
            :style="{ left: `${cell.x}px`, top: `${cell.y}px` }"
            :disabled="!cell.skill"
            :aria-pressed="cell.key === selectedKey"
            @click="selectedKey = cell.key"
          >
            <span class="hi">
              <template v-if="cell.skill">
                <span class="hi-icon" aria-hidden="true">{{ skillIcons[cell.skill.state] }}</span>
                <span class="hi-name">{{ cell.skill.name }}</span>
                <span class="hi-sub">{{ skillSub(cell.skill) }}</span>
              </template>
              <template v-else>
                <span class="hi-icon" aria-hidden="true">+</span>
                <span class="hi-name">Новый курс</span>
                <span class="hi-sub">скоро</span>
              </template>
            </span>
          </button>
          <span
            v-if="here"
            class="hexmap-here"
            :style="{ left: `${here.x + HEX.width / 2}px`, top: `${here.y - 12}px` }"
            >Ты здесь</span
          >
        </div>
      </div>

      <aside class="hexmap-side">
        <div v-if="selected?.skill" class="hexmap-card hexmap-selected">
          <span class="hexmap-kicker">ВЫБРАНА СОТА</span>
          <strong class="hexmap-title">{{ selected.skill.name }}</strong>
          <span class="hexmap-muted">{{
            skillAbout(selected.skill, selectedCourse?.title ?? "")
          }}</span>
          <div v-if="selected.skill.steps_total" class="hexmap-segments" aria-hidden="true">
            <span
              v-for="(kind, index) in skillSegments(selected.skill)"
              :key="index"
              :class="`seg--${kind}`"
            />
          </div>
          <span v-if="selected.skill.steps_total" class="hexmap-muted hexmap-small">{{
            skillCountsText(selected.skill)
          }}</span>
          <RouterLink
            v-if="selected.skill.next_step_id && selected.skill.state !== 'locked'"
            class="hexmap-continue"
            :to="{
              name: STUDENT_STEP_ROUTE.name,
              params: { courseId: selected.courseId, stepId: selected.skill.next_step_id },
            }"
            >Продолжить →</RouterLink
          >
        </div>

        <div class="hexmap-card hexmap-legend">
          <b>Как читать соты</b>
          <span><b class="legend-gold">★</b> Золотая — с первой попытки на максимум</span>
          <span><b class="legend-done">✓</b> Зелёная — навык освоен</span>
          <span><b class="legend-progress">●</b> С синей рамкой — в процессе</span>
          <span><b class="legend-open">○</b> Белая — можно начать</span>
          <span class="hexmap-muted">Пунктир — откроется после соседних</span>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.hexmap {
  display: flex;
  flex-direction: column;
  gap: 14px;
  color: #0f172a;
  font-size: 15px;
  line-height: 1.5;
  font-variant-numeric: tabular-nums;
}
.hexmap-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 16px;
}
.hexmap-head h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 800;
}
.hexmap-head span,
.hexmap-muted {
  color: #4a546b;
  font-size: 15px;
}
.hexmap-state {
  margin: 0;
  padding: 40px 20px;
  border: 1px dashed #cbd3e2;
  border-radius: 16px;
  color: #4a546b;
  text-align: center;
}
.hexmap-state--error {
  color: #9a3c3c;
}
.hexmap-body {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.hexmap-board-wrap {
  flex: 1 1 auto;
  min-width: 0;
  overflow: auto;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.hexmap-board {
  position: relative;
}
.hexmap-label {
  position: absolute;
  color: #4a546b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  white-space: nowrap;
}
.hexmap-label--soon {
  color: #7c869c;
}

/* A cell: the outer hexagon is the border, the inner one the fill. */
.hx {
  position: absolute;
  width: 130px;
  height: 112px;
  padding: 0;
  border: 0;
  clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%);
  background: var(--hx-border);
  font: inherit;
  cursor: pointer;
}
.hx:disabled {
  cursor: default;
}
.hi {
  position: absolute;
  inset: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 0 18px;
  clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%);
  background: var(--hx-fill);
  color: var(--hx-text);
  text-align: center;
}
.hi-icon {
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}
.hi-name {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.15;
  overflow-wrap: anywhere;
}
.hi-sub {
  font-size: 11px;
  line-height: 1.2;
  opacity: 0.85;
}
.hx--gold {
  --hx-border: #d4a017;
  --hx-fill: #e8b21e;
  --hx-text: #fff;
}
.hx--done {
  --hx-border: #17915a;
  --hx-fill: #17915a;
  --hx-text: #fff;
}
.hx--in_progress {
  --hx-border: #3457f0;
  --hx-fill: #fff;
  --hx-text: #0f172a;
}
.hx--open {
  --hx-border: #8a93a8;
  --hx-fill: #fff;
  --hx-text: #0f172a;
}
.hx--locked,
.hx--soon {
  --hx-text: #7c869c;
}
.hx--locked {
  --hx-border: #d5dbe6;
  --hx-fill: #f4f6fb;
}
.hx--soon {
  --hx-border: #e1e6f0;
  --hx-fill: #fff;
}
.hx--locked .hi,
.hx--soon .hi {
  background-image: repeating-linear-gradient(
    135deg,
    transparent 0 8px,
    rgba(225, 230, 240, 0.6) 8px 10px
  );
}
.hx--current {
  --hx-border: #3457f0;
}
.hx--current.hx--in_progress .hi,
.hx--current.hx--open .hi {
  inset: 6px;
  background: #eaf0fe;
}
.hx--selected {
  filter: drop-shadow(0 0 6px rgba(52, 87, 240, 0.45));
}
.hx:focus-visible {
  outline: none;
  filter: drop-shadow(0 0 0 #3457f0) drop-shadow(0 0 4px #3457f0);
}
.hexmap-here {
  position: absolute;
  padding: 2px 10px;
  transform: translateX(-50%);
  border-radius: 999px;
  background: #3457f0;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  pointer-events: none;
}

.hexmap-side {
  display: flex;
  flex: 0 0 320px;
  flex-direction: column;
  gap: 12px;
}
.hexmap-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.hexmap-kicker {
  color: #4a546b;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.hexmap-title {
  font-size: 24px;
  font-weight: 800;
  line-height: 1.1;
}
.hexmap-small {
  font-size: 14px;
}
.hexmap-segments {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}
.hexmap-segments span {
  flex-grow: 1;
  height: 10px;
  border-radius: 3px;
}
.seg--completed {
  background: #17915a;
}
.seg--checking {
  background: #6e4fe8;
}
.seg--returned {
  background: #b8520f;
}
.seg--ahead {
  background: #e1e6f0;
}
.hexmap-continue {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  margin-top: 8px;
  border-radius: 14px;
  background: #3457f0;
  color: #fff;
  font-weight: 700;
  text-decoration: none;
}
.hexmap-continue:hover {
  background: #2641c9;
}
.hexmap-legend b {
  font-size: 16px;
}
.legend-gold {
  color: #d4a017;
}
.legend-done {
  color: #17915a;
}
.legend-progress {
  color: #3457f0;
}
.legend-open {
  color: #5e677d;
}
@media (max-width: 1000px) {
  .hexmap-body {
    flex-direction: column;
    align-items: stretch;
  }
  .hexmap-side {
    flex-basis: auto;
  }
}
</style>
