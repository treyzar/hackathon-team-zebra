<script setup lang="ts">
import { RouterLink } from "vue-router";
import type { Course } from "../types";
import { progressText, stepLabels } from "../presentation";
import { STUDENT_COURSES_ROUTE } from "@/pages/student/courses/constants";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";

defineProps<{
  course: Course;
  selectedStepId?: number;
  titles: Map<number, string>;
}>();

function deadlineLabel(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU");
}
</script>

<template>
  <aside class="student-outline" aria-label="Модули и шаги курса">
    <div class="student-outline-head">
      <RouterLink :to="{ name: STUDENT_COURSES_ROUTE.name }" class="student-back-link"
        >← Мои курсы</RouterLink
      >
      <h2>{{ course.title }}</h2>
      <p>{{ progressText(course.progress.steps_completed, course.progress.steps_total) }}</p>
      <div class="student-outline-progress">
        <span :style="{ width: `${course.progress.percent}%` }" />
      </div>
    </div>

    <nav class="student-outline-scroll">
      <section
        v-for="(module, moduleIndex) in course.modules"
        :key="module.id"
        class="student-outline-module"
      >
        <h3>{{ moduleIndex + 1 }}. {{ module.title }}</h3>
        <div v-for="(item, stepIndex) in module.steps" :key="item.id">
          <span
            v-if="item.locked"
            class="student-outline-step student-outline-step--locked"
            title="Шаг ещё закрыт"
          >
            <span class="student-step-icon student-step-icon--locked" aria-hidden="true">○</span>
            <span
              >{{ stepLabels[item.type]
              }}<small>{{ moduleIndex + 1 }}.{{ stepIndex + 1 }}</small></span
            >
            <small v-if="item.deadline" class="student-step-deadline">{{
              deadlineLabel(item.deadline.due_at)
            }}</small>
          </span>

          <RouterLink
            v-else
            class="student-outline-step"
            :class="{ 'student-outline-step--active': item.id === selectedStepId }"
            :to="{
              name: STUDENT_STEP_ROUTE.name,
              params: { courseId: course.id, stepId: item.id },
            }"
          >
            <span
              class="student-step-icon"
              :class="`student-step-icon--${item.progress.state}`"
              aria-hidden="true"
            >
              {{
                item.progress.state === "passed"
                  ? "✓"
                  : item.progress.state === "checking"
                    ? "◷"
                    : item.progress.state === "failed" ||
                        item.progress.state === "attempts_exhausted"
                      ? "↺"
                      : item.id === selectedStepId
                        ? "●"
                        : "○"
              }}
            </span>
            <span
              >{{ titles.get(item.id) || stepLabels[item.type]
              }}<small>{{ moduleIndex + 1 }}.{{ stepIndex + 1 }}</small></span
            >
            <small v-if="item.deadline" class="student-step-deadline">{{
              deadlineLabel(item.deadline.due_at)
            }}</small>
          </RouterLink>
        </div>
      </section>
      <p v-if="!course.modules.length" class="student-outline-empty">
        Модули пока не опубликованы.
      </p>
    </nav>
  </aside>
</template>

<style scoped>
.student-outline {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-right: 1px solid #e1e6f0;
}
.student-outline-head {
  flex: none;
  padding: 24px 20px 17px;
  border-bottom: 1px solid #edf0f6;
}
.student-back-link {
  color: #3457f0;
  font-size: var(--font-size-small);
  font-weight: 650;
  text-decoration: none;
}
.student-outline-head h2 {
  margin: 16px 0 5px;
  font-size: 20px;
  line-height: 1.25;
}
.student-outline-head p {
  margin: 0 0 13px;
  color: #5e677d;
  font-size: var(--font-size-small);
}
.student-outline-progress {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #e1e6f0;
}
.student-outline-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #3457f0;
}
.student-outline-scroll {
  min-height: 0;
  overflow-y: auto;
  padding: 11px 13px 28px;
}
.student-outline-module h3 {
  margin: 18px 7px 9px;
  color: #5e677d;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.07em;
  line-height: 1.4;
  text-transform: uppercase;
}
.student-outline-step {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: var(--button-height);
  padding: 8px 10px;
  border-radius: 10px;
  color: #27344d;
  font-size: var(--font-size-base);
  line-height: 1.3;
  text-decoration: none;
}
.student-outline-step small {
  display: block;
  color: #7b8497;
  font-size: var(--font-size-small);
}
.student-outline-step > span:nth-child(2) {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
.student-step-deadline {
  flex: none;
  margin-left: auto;
  color: #9a5a21;
}
.student-outline-step:hover:not(.student-outline-step--locked) {
  background: #f3f6ff;
}
.student-outline-step--active {
  background: #eaf0fe;
  box-shadow: inset 0 0 0 2px #c9d5fc;
  font-weight: 700;
}
.student-outline-step--locked {
  color: #8a93a8;
  cursor: not-allowed;
}
.student-step-icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 25px;
  height: 25px;
  border: 1.5px solid #8a93a8;
  border-radius: 50%;
  color: #5e677d;
  font-size: var(--font-size-small);
}
.student-step-icon--passed {
  border: 0;
  background: #e4f5ec;
  color: #17915a;
  font-weight: 800;
}
.student-step-icon--checking {
  border: 0;
  background: #efebfe;
  color: #6e4fe8;
}
.student-step-icon--failed,
.student-step-icon--attempts_exhausted,
.student-step-icon--partial {
  border: 0;
  background: #fff1e6;
  color: #b8520f;
}
.student-outline-step--active .student-step-icon:not(.student-step-icon--passed) {
  border: 0;
  background: #3457f0;
  color: #fff;
}
.student-outline-empty {
  margin: 16px 8px;
  color: #7b8497;
  font-size: var(--font-size-small);
}
@media (max-width: 650px) {
  .student-outline {
    border-right: 0;
    border-bottom: 1px solid #e1e6f0;
  }
  .student-outline-head {
    padding: 13px 17px 10px;
  }
  .student-outline-head h2 {
    margin: 7px 0 2px;
    font-size: 16px;
  }
  .student-outline-head p {
    margin-bottom: 6px;
  }
  .student-outline-scroll {
    padding-top: 0;
  }
}
</style>
