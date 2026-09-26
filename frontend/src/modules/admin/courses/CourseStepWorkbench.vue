<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { ADMIN_STEP_ROUTE } from "@/pages/admin/step/constants";
import { stepApi } from "../steps/api";
import { formFromStep, payloadFromForm, validateStepForm } from "../steps/editor-model";
import RichTextEditor from "../steps/RichTextEditor.vue";
import { stepTypeLabels } from "../shared/format";
import type { Step } from "../shared/types";

const props = defineProps<{
  stepId: number;
  courseId: number;
  number: string;
  moduleTitle: string;
}>();
const emit = defineEmits<{ saved: [] }>();
const step = ref<Step | null>(null);
const form = ref<ReturnType<typeof formFromStep> | null>(null);
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
const editorValid = ref(true);
const imageUploading = ref(false);
const isBreaking = ref(false);
const gradingLabel = computed(() =>
  step.value?.type === "theory"
    ? "При прочтении"
    : step.value?.type === "free_text"
      ? "Куратор"
      : step.value?.type === "programming" && form.value?.grading !== "manual"
        ? "Автотесты"
        : step.value?.type === "programming"
          ? "Куратор"
          : "Авто",
);

const shortTextAccepted = computed(() =>
  (form.value?.shortTextAccepted ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean),
);

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    const result = await stepApi.step(props.stepId);
    step.value = result;
    form.value = formFromStep(result);
    editorValid.value = true;
    isBreaking.value = false;
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}

async function save(): Promise<void> {
  if (!step.value || !form.value || imageUploading.value) return;
  if (!editorValid.value) {
    error.value = "Исправьте содержимое шага перед сохранением.";
    return;
  }
  error.value = validateStepForm(form.value) ?? "";
  if (error.value) return;
  saving.value = true;
  success.value = "";
  try {
    const saved = await stepApi.saveStep(step.value.id, {
      payload: payloadFromForm(form.value),
      base_revision: step.value.revision.number,
      is_breaking: isBreaking.value,
      comment: "Правка в конструкторе курса",
    });
    step.value = saved;
    form.value = formFromStep(saved);
    isBreaking.value = false;
    success.value = `Редакция ${saved.revision.number} сохранена`;
    emit("saved");
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    saving.value = false;
  }
}

watch(() => props.stepId, load, { immediate: true });
</script>

<template>
  <section class="course-workbench">
    <p v-if="loading" class="admin-empty">Загружаем шаг…</p>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="success" class="admin-success" role="status">{{ success }}</p>
    <template v-if="form && step && !loading">
      <div class="workbench-eyebrow">
        Шаг {{ number }} · редактор типа «{{ stepTypeLabels[step.type] }}»
      </div>
      <p class="workbench-module">{{ moduleTitle }}</p>
      <div class="workbench-top-row">
        <label class="admin-field workbench-title"
          >Название
          <input v-model="form.title" maxlength="200" placeholder="Название шага" />
        </label>
        <div class="admin-field workbench-grading">
          <span>Проверка</span>
          <div class="workbench-readonly">{{ gradingLabel }}</div>
        </div>
        <label v-if="step.type !== 'theory'" class="admin-field workbench-points"
          >Баллы
          <input v-model.number="form.maxScore" type="number" min="0" max="1000" />
        </label>
      </div>
      <label class="admin-field workbench-body"
        >{{
          step.type === "theory"
            ? "Текст"
            : step.type === "programming"
              ? "Условие"
              : "Вопрос или задание"
        }}
        <RichTextEditor
          :key="`${step.id}-${step.revision.number}`"
          v-model="form.body"
          @error="error = $event"
          @validity="editorValid = $event"
          @uploading="imageUploading = $event"
        />
      </label>
      <div
        v-if="step.type === 'single_choice' || step.type === 'multiple_choice'"
        class="workbench-answer-list"
      >
        <b>Варианты ответа</b>
        <div v-for="(option, index) in form.options" :key="option.id" class="workbench-answer">
          <span
            class="admin-badge"
            :class="option.correct ? 'admin-badge--green' : 'admin-badge--gray'"
            >{{ option.correct ? "✓" : "○" }}</span
          >
          <span>{{ index + 1 }}. {{ option.text }}</span>
        </div>
      </div>
      <div v-if="step.type === 'free_text' && form.criteria" class="workbench-answer-list">
        <b>Критерии проверки · для куратора</b>
        <p>{{ form.criteria }}</p>
      </div>
      <div v-if="step.type === 'short_text'" class="workbench-answer-list">
        <b
          >Правильные ответы<template v-if="form.shortTextCaseSensitive">
            · с учётом регистра</template
          ></b
        >
        <div v-for="answer in shortTextAccepted" :key="answer" class="workbench-answer">
          <span class="admin-badge admin-badge--green">✓</span>
          <span>{{ answer }}</span>
        </div>
        <p v-if="!shortTextAccepted.length" class="admin-muted">
          Список пуст — ответ проверяет куратор вручную.
        </p>
        <p v-else-if="form.shortTextGrading === 'manual'" class="admin-muted">
          Проверка вручную: список для куратора — подсказка.
        </p>
      </div>

      <div v-if="step.type === 'number'" class="workbench-answer-list">
        <b>Правильный ответ</b>
        <div class="workbench-answer">
          <span class="admin-badge admin-badge--green">✓</span>
          <span>{{ form.numberValue || "—" }}</span>
        </div>
        <p class="admin-muted">
          <template v-if="form.numberKind === 'decimal'">
            Дробное, точность — {{ form.numberPrecision }}
            {{ form.numberPrecision === 1 ? "знак" : "знаков" }} после запятой.
          </template>
          <template v-else>Целое число.</template>
        </p>
      </div>
      <div v-if="step.type === 'programming'" class="workbench-answer-list">
        <b>Задача с тестами</b>
        <p>
          {{ form.testGroups.length }} групп тестов · {{ form.timeLimitMs }} мс ·
          {{ form.memoryLimitMb }} МБ
        </p>
      </div>
      <div class="workbench-footer">
        <label class="admin-check"
          ><input v-model="isBreaking" type="checkbox" /> Существенное изменение ответа</label
        >
        <div class="admin-actions">
          <RouterLink
            class="admin-button"
            :to="{ name: ADMIN_STEP_ROUTE.name, params: { stepId: step.id }, query: { courseId } }"
            >Все настройки</RouterLink
          >
          <button
            class="admin-button admin-button--primary"
            type="button"
            :disabled="saving || imageUploading"
            @click="save"
          >
            {{ saving ? "Сохраняем…" : "Сохранить редакцию" }}
          </button>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.course-workbench {
  display: grid;
  align-content: start;
  gap: 15px;
  min-width: 0;
  padding: 20px 28px;
}
.workbench-eyebrow {
  margin: 0;
  color: #4a546b;
  font-size: 13px;
}
.workbench-module {
  margin: -11px 0 0;
  color: #7c869c;
  font-size: 12px;
}
.workbench-top-row {
  display: flex;
  align-items: end;
  gap: 12px;
}
.workbench-title {
  flex: 1;
}
.workbench-grading {
  width: 160px;
}
.workbench-points {
  width: 82px;
}
.workbench-readonly {
  display: flex;
  align-items: center;
  min-height: 40px;
  padding: 0 11px;
  border: 1px solid #e1e6f0;
  border-radius: 9px;
  background: #f4f6fb;
  font-size: 13px;
}
.workbench-body {
  --quill-editor-min-height: 240px;
}
.workbench-answer-list {
  display: grid;
  gap: 8px;
  font-size: 13px;
}
.workbench-answer-list p {
  margin: 0;
  color: #4a546b;
}
.workbench-answer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 11px;
  border: 1px solid #e1e6f0;
  border-radius: 9px;
  background: #fff;
}
.workbench-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 4px;
}
@media (max-width: 700px) {
  .workbench-top-row {
    flex-wrap: wrap;
  }
  .workbench-title {
    flex-basis: 100%;
  }
  .course-workbench {
    padding: 20px;
  }
}
</style>
