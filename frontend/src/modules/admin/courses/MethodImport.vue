<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { ADMIN_COURSES_ROUTE } from "@/pages/admin/courses/constants";
import { courseApi } from "./api";
import { parseMethodText } from "./method-parser";
import type { Course } from "../shared/types";

const source = ref("");
const parsed = ref<ReturnType<typeof parseMethodText> | null>(null);
const courses = ref<Course[]>([]);
const selectedCourse = ref<number | "">("");
const fileInput = ref<HTMLInputElement | null>(null);
const error = ref("");
const unsupportedCount = computed(
  () => parsed.value?.steps.filter((step) => !step.supported).length ?? 0,
);

async function readFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".txt")) {
    error.value = "Сейчас можно открыть только .txt. Разбор .docx требует серверной поддержки.";
    return;
  }
  source.value = await file.text();
  parsed.value = null;
  error.value = "";
}
function parse(): void {
  parsed.value = parseMethodText(source.value);
  error.value = parsed.value.steps.length ? "" : "Не удалось найти строки, начинающиеся с «Шаг».";
}
onMounted(async () => {
  try {
    courses.value = await courseApi.courses();
    selectedCourse.value = courses.value[0]?.id ?? "";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  }
});
</script>

<template>
  <div class="admin-page admin-page--detail method-page">
    <Teleport defer to="#admin-page-header">
      <div class="admin-toolbar admin-toolbar--detail">
        <div class="method-heading">
          <RouterLink class="admin-link" :to="ADMIN_COURSES_ROUTE.path">← Курсы</RouterLink>
          <h2>Импорт методички</h2>
        </div>
        <p>Вставьте текст методички для предварительного разбора курса, модулей и шагов</p>
      </div>
    </Teleport>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <div class="method-layout">
      <section class="method-source">
        <label for="method-text">Текст методички</label>
        <textarea
          id="method-text"
          v-model="source"
          placeholder="Модуль 1.3. События и условия\n\nШаг 1.3.2. Проверь себя: условия\nТип шага   Контрольный вопрос\nПроверка   Автоматическая"
        />
        <div class="admin-actions">
          <button
            class="admin-button admin-button--primary"
            type="button"
            :disabled="!source.trim()"
            @click="parse"
          >
            Разобрать
          </button>
          <button class="admin-button" type="button" @click="fileInput?.click()">
            Загрузить .txt
          </button>
          <input
            ref="fileInput"
            class="method-file"
            type="file"
            accept=".txt,text/plain"
            aria-label="Загрузить текст методички"
            @change="readFile"
          />
        </div>
      </section>
      <section class="method-result">
        <div class="method-summary">
          <div>
            <strong>✓ {{ parsed?.steps.length ?? 0 }} шагов распознано</strong> ·
            {{ parsed?.modules ?? 0 }} модулей
          </div>
          <div v-if="unsupportedCount">
            <strong>! {{ unsupportedCount }} требует внимания</strong>
          </div>
        </div>
        <div class="admin-table-wrap">
          <table class="admin-table">
            <thead>
              <tr>
                <th>№</th>
                <th>Шаг</th>
                <th>Тип</th>
                <th>Проверка</th>
                <th>Распознано</th>
              </tr>
            </thead>
            <tbody v-if="parsed?.steps.length">
              <tr
                v-for="step in parsed.steps"
                :key="`${step.number}-${step.title}`"
                :class="{ 'method-unsupported': !step.supported }"
              >
                <td>{{ step.number }}</td>
                <td>
                  <strong>{{ step.title }}</strong>
                </td>
                <td>
                  <span class="admin-badge">{{ step.type }}</span>
                </td>
                <td>{{ step.grading }}</td>
                <td>{{ step.supported ? step.details : "Нет типа в API" }}</td>
              </tr>
            </tbody>
            <tbody v-else>
              <tr>
                <td colspan="5" class="admin-empty">Вставьте текст и нажмите «Разобрать»</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="method-footer">
          <label class="admin-field"
            >В курс
            <select v-model="selectedCourse">
              <option value="">Выберите курс</option>
              <option v-for="course in courses" :key="course.id" :value="course.id">
                {{ course.title }}
              </option>
            </select>
          </label>
          <button
            class="admin-button admin-button--primary"
            type="button"
            disabled
            title="В текущем API нет операции импорта методички"
          >
            Создать {{ parsed?.steps.length ?? 0 }} шагов →
          </button>
        </div>
        <p class="admin-muted">
          Сохранение распознанной методички появится после добавления импорта в API.
        </p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.admin-toolbar {
  justify-content: start;
  gap: 18px;
}
.method-heading {
  display: flex;
  align-items: center;
  gap: 16px;
}
.method-heading h2 {
  font-size: 18px;
}
.admin-toolbar p {
  margin: 0;
}
.method-layout {
  display: grid;
  grid-template-columns: 440px minmax(0, 1fr);
  gap: 20px;
  min-height: 570px;
}
.method-source {
  display: grid;
  grid-template-rows: auto minmax(400px, 1fr) auto;
  align-content: start;
  gap: 8px;
}
.method-source label {
  font-weight: 600;
}
.method-source textarea {
  width: 100%;
  min-height: 400px;
  padding: 12px;
  border: 1px solid #e1e6f0;
  border-radius: 8px;
  background: #fff;
  color: #0f172a;
  font:
    12px/1.6 "JetBrains Mono",
    monospace;
  resize: vertical;
}
.method-file {
  display: none;
}
.method-result {
  display: grid;
  align-content: start;
  gap: 12px;
  min-width: 0;
}
.method-summary {
  display: flex;
  gap: 12px;
  font-size: 13px;
}
.method-summary > div {
  padding: 12px 16px;
  border-radius: 12px;
  background: #e4f5ec;
}
.method-summary > div:first-child {
  flex: 1;
}
.method-summary > div:first-child strong {
  color: #17915a;
}
.method-summary > div:last-child:not(:first-child) {
  background: #fff1e6;
  color: #b8520f;
}
.method-result .admin-table {
  min-width: 580px;
}
.method-unsupported {
  background: #fff1e6;
}
.method-footer {
  display: flex;
  align-items: end;
  gap: 12px;
}
.method-footer .admin-field {
  flex: 1;
}
.method-result > .admin-muted {
  margin: 0;
}
@media (max-width: 1100px) {
  .method-layout {
    grid-template-columns: 1fr;
  }
}
</style>
