<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { courseApi, type CourseImportResult } from "@/modules/admin/courses/api";
import type { Course } from "@/modules/admin/shared/types";
import { ADMIN_COURSE_ROUTE } from "@/pages/admin/course/constants";

const courses = ref<Course[]>([]);
const selectedCourseId = ref<number | "">("");
const selectedCourse = computed(() =>
  courses.value.find((course) => course.id === selectedCourseId.value),
);
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const importedCourse = ref<CourseImportResult | null>(null);
const loadingCourses = ref(true);
const importing = ref(false);
const exporting = ref<"json" | "pdf" | "">("");
const dragging = ref(false);
const loadError = ref("");
const importError = ref("");
const exportError = ref("");

async function loadCourses(): Promise<void> {
  loadingCourses.value = true;
  loadError.value = "";
  try {
    courses.value = await courseApi.courses();
    if (!courses.value.some((course) => course.id === selectedCourseId.value)) {
      selectedCourseId.value = courses.value[0]?.id ?? "";
    }
  } catch (cause) {
    loadError.value = getApiErrorMessage(cause);
  } finally {
    loadingCourses.value = false;
  }
}

function chooseFile(file: File | undefined): void {
  importedCourse.value = null;
  importError.value = "";
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".json")) {
    selectedFile.value = null;
    importError.value = "Выберите файл с расширением .json.";
    return;
  }
  selectedFile.value = file;
}

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  chooseFile(input.files?.[0]);
  input.value = "";
}

function onDrop(event: DragEvent): void {
  dragging.value = false;
  chooseFile(event.dataTransfer?.files[0]);
}

async function importCourse(): Promise<void> {
  if (!selectedFile.value) return;
  importing.value = true;
  importError.value = "";
  importedCourse.value = null;
  try {
    importedCourse.value = await courseApi.importCourse(selectedFile.value);
    selectedFile.value = null;
    await loadCourses();
    selectedCourseId.value = importedCourse.value.course_id;
  } catch (cause) {
    importError.value = getApiErrorMessage(cause);
  } finally {
    importing.value = false;
  }
}

function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

async function exportCourse(format: "json" | "pdf"): Promise<void> {
  if (!selectedCourse.value) return;
  exporting.value = format;
  exportError.value = "";
  try {
    const blob =
      format === "json"
        ? await courseApi.exportCourseJson(selectedCourse.value.id)
        : await courseApi.exportCoursePdf(selectedCourse.value.id);
    download(blob, `${selectedCourse.value.slug}.${format}`);
  } catch (cause) {
    exportError.value = getApiErrorMessage(cause);
  } finally {
    exporting.value = "";
  }
}

onMounted(loadCourses);
</script>

<template>
  <div class="admin-page admin-page--detail exchange-page">
    <Teleport defer to="#admin-page-header">
      <div class="admin-toolbar admin-toolbar--detail">
        <div>
          <RouterLink class="admin-link" to="/admin/courses">← Курсы</RouterLink>
          <h2>Импорт / экспорт курса</h2>
        </div>
      </div>
    </Teleport>

    <p v-if="loadError" class="admin-error" role="alert">{{ loadError }}</p>

    <div class="exchange-grid">
      <section class="admin-panel exchange-panel">
        <div class="admin-panel-head">
          <div>
            <h2>Импорт</h2>
            <p>JSON-файл курса</p>
          </div>
          <span class="exchange-format">.JSON</span>
        </div>

        <div
          class="exchange-dropzone"
          :class="{ 'exchange-dropzone--active': dragging, 'exchange-dropzone--selected': selectedFile }"
          @dragenter.prevent="dragging = true"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <input
            ref="fileInput"
            class="exchange-file-input"
            type="file"
            accept=".json,application/json"
            aria-label="Выбрать JSON-файл курса"
            @change="onFileChange"
          />
          <span class="exchange-file-icon" aria-hidden="true">↑</span>
          <strong>{{ selectedFile?.name ?? "Файл курса" }}</strong>
          <button
            class="admin-button"
            type="button"
            :disabled="importing"
            @click="fileInput?.click()"
          >
            {{ selectedFile ? "Выбрать другой файл" : "Выбрать JSON-файл" }}
          </button>
        </div>

        <p v-if="importError" class="admin-error" role="alert">{{ importError }}</p>
        <div class="exchange-actions">
          <button
            class="admin-button admin-button--primary"
            type="button"
            :disabled="!selectedFile || importing"
            @click="importCourse"
          >
            {{ importing ? "Импортируем…" : "Импортировать курс" }}
          </button>
        </div>

        <div v-if="importedCourse" class="exchange-result" role="status">
          <div class="exchange-result-heading">
            <strong>Курс импортирован</strong>
            <RouterLink
              class="admin-link"
              :to="{
                name: ADMIN_COURSE_ROUTE.name,
                params: { courseId: importedCourse.course_id },
              }"
            >
              Открыть курс →
            </RouterLink>
          </div>
          <span>{{ importedCourse.title }}</span>
          <ul v-if="importedCourse.warnings.length" class="exchange-warnings">
            <li v-for="warning in importedCourse.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>
      </section>

      <section class="admin-panel exchange-panel">
        <div class="admin-panel-head">
          <div>
            <h2>Экспорт</h2>
            <p>Скачать курс в файл</p>
          </div>
          <span class="exchange-format">JSON · PDF</span>
        </div>

        <label class="admin-field" for="export-course">Курс</label>
        <select
          id="export-course"
          v-model="selectedCourseId"
          class="admin-input exchange-course-select"
          :disabled="loadingCourses || !courses.length"
        >
          <option v-if="loadingCourses || !courses.length" value="" disabled>
            {{ loadingCourses ? "Загружаем курсы…" : "Курсы не найдены" }}
          </option>
          <option v-for="course in courses" :key="course.id" :value="course.id">
            {{ course.title }}
          </option>
        </select>
        <p v-if="exportError" class="admin-error" role="alert">{{ exportError }}</p>

        <div class="exchange-actions">
          <button
            class="admin-button admin-button--primary"
            type="button"
            :disabled="!selectedCourse || Boolean(exporting)"
            @click="exportCourse('json')"
          >
            <span aria-hidden="true">↓</span>
            {{ exporting === "json" ? "Готовим JSON…" : "Скачать JSON" }}
          </button>
          <button
            class="admin-button"
            type="button"
            :disabled="!selectedCourse || Boolean(exporting)"
            @click="exportCourse('pdf')"
          >
            <span aria-hidden="true">↓</span>
            {{ exporting === "pdf" ? "Готовим PDF…" : "Скачать PDF" }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.admin-toolbar--detail > div:first-child {
  gap: 16px;
}
.exchange-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 20px;
}
.exchange-panel {
  display: grid;
  gap: 18px;
  min-width: 0;
}
.exchange-panel .admin-panel-head {
  align-items: center;
  margin: 0;
}
.exchange-format {
  padding: 5px 9px;
  border-radius: 4px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
}
.exchange-dropzone {
  display: grid;
  justify-items: center;
  gap: 12px;
  min-height: 220px;
  padding: 24px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-bg);
  text-align: center;
  transition: border-color 120ms ease, background-color 120ms ease;
}
.exchange-dropzone--active,
.exchange-dropzone--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.exchange-dropzone strong {
  max-width: 100%;
  overflow-wrap: anywhere;
}
.exchange-file-input {
  display: none;
}
.exchange-file-icon {
  display: grid;
  width: 42px;
  aspect-ratio: 1;
  place-items: center;
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-primary);
  font-size: 24px;
  line-height: 1;
}
.exchange-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.exchange-result {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border-left: 3px solid var(--color-success);
  background: var(--color-success-soft);
}
.exchange-result-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.exchange-warnings {
  display: grid;
  gap: 4px;
  margin: 0;
  padding-left: 20px;
  color: var(--color-warning);
  font-size: 13px;
}
.exchange-course-select {
  margin-top: -14px;
}
@media (max-width: 760px) {
  .exchange-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
