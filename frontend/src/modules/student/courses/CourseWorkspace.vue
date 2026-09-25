<script setup lang="ts">
import { toRef } from "vue";
import CourseOutline from "./components/CourseOutline.vue";
import CourseOverview from "./components/CourseOverview.vue";
import StepPlayer from "@/modules/student/steps/StepPlayer.vue";
import { useCourseWorkspace } from "./composables/useCourseWorkspace";

const props = defineProps<{ courseId: number; stepId?: number }>();
const state = useCourseWorkspace(toRef(props, "courseId"), toRef(props, "stepId"));
</script>

<template>
  <div class="student-workspace">
    <div v-if="state.loading.value" class="student-workspace-loading" role="status">
      Загружаем курс…
    </div>
    <div
      v-else-if="!state.course.value"
      class="student-workspace-loading student-workspace-error"
      role="alert"
    >
      {{ state.error.value }} <button type="button" @click="state.loadCourse">Повторить</button>
    </div>

    <template v-else>
      <CourseOutline
        :course="state.course.value"
        :selected-step-id="stepId"
        :titles="state.titles.value"
      />

      <section class="student-workspace-main" aria-label="Материал курса">
        <div v-if="state.error.value" class="student-workspace-error" role="alert">
          {{ state.error.value }}
        </div>

        <template v-if="stepId">
          <div v-if="state.selectedSummary.value?.locked" class="student-step-unavailable">
            <h2>Шаг пока закрыт</h2>
            <p>Завершите предыдущие шаги курса, чтобы открыть этот.</p>
          </div>
          <div v-else-if="state.stepLoading.value" class="student-workspace-loading" role="status">
            Загружаем шаг…
          </div>
          <StepPlayer
            v-else-if="state.step.value"
            :key="state.step.value.id"
            :step="state.step.value"
            :number="state.stepNumber.value"
            @refresh="state.refresh"
          />
          <div v-else class="student-step-unavailable">
            <h2>Шаг не найден</h2>
            <p>Вернитесь к оглавлению курса.</p>
          </div>
        </template>

        <CourseOverview v-else :course="state.course.value" />
      </section>
    </template>
  </div>
</template>

<style scoped>
.student-workspace {
  display: grid;
  grid-template-columns: 310px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  min-height: 0;
  color: #0f172a;
  background: #f4f6fb;
}
.student-workspace-main {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 32px clamp(25px, 4vw, 52px) 65px;
}
.student-workspace-loading,
.student-step-unavailable {
  padding: 35px;
  color: #65728a;
}
.student-workspace > .student-workspace-loading {
  grid-column: 1/-1;
}
.student-workspace-error {
  margin: 0 0 20px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #fcebeb;
  color: #a53b3b;
}
.student-workspace-error button {
  color: #3457f0;
  font-weight: 700;
}
@media (max-width: 900px) {
  .student-workspace {
    grid-template-columns: 245px minmax(0, 1fr);
  }
}
@media (max-width: 650px) {
  .student-workspace {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(170px, 32%) minmax(0, 1fr);
  }
  .student-workspace-main {
    padding: 25px 20px 50px;
  }
}
</style>
