<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { stepApi } from "./api";
import type { CodeSample } from "./editor-model";
import { uploadAnswerFile } from "./file-api";
import RichTextEditor from "./RichTextEditor.vue";
import StepTypePicker from "./StepTypePicker.vue";
import {
  newStepForm,
  formFromStep,
  payloadFromForm,
  validateStepForm,
} from "./editor-model";
import { stepTypeLabels } from "../shared/format";
import type { Step, StepType } from "../shared/types";
import { ADMIN_COURSE_ROUTE } from "@/pages/admin/course/constants";
import { ADMIN_COURSES_ROUTE } from "@/pages/admin/courses/constants";
import { ADMIN_REVISIONS_ROUTE } from "@/pages/admin/revisions/constants";
import { ADMIN_STEP_ROUTE } from "@/pages/admin/step/constants";

const route = useRoute();
const router = useRouter();
const isNew = computed(() => route.name === "admin-step-new");
const stepId = computed(() => Number(route.params.stepId));
const courseId = computed(() => Number(route.query.courseId));
const backRoute = computed(() =>
  Number.isInteger(courseId.value) && courseId.value > 0
    ? { name: ADMIN_COURSE_ROUTE.name, params: { courseId: courseId.value } }
    : { name: ADMIN_COURSES_ROUTE.name },
);
const step = ref<Step | null>(null);
const form = ref(newStepForm());
const comment = ref("");
const isBreaking = ref(false);
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const success = ref("");
const editorValid = ref(true);
const uploading = ref(false);
const imageUploading = ref(false);
const showTypePicker = ref(isNew.value);
const hasChosenType = ref(false);
const submissionMode = computed(() => {
  if (form.value.type !== "free_text") return "custom";
  if (form.value.requireText && form.value.maxFiles === 0) return "link";
  if (!form.value.requireText && form.value.minFiles === 1 && form.value.maxFiles === 1) return "file";
  if (!form.value.requireText && form.value.minFiles === 0 && form.value.maxFiles === 1) return "either";
  return "custom";
});

function setSubmissionMode(mode: "link" | "file" | "either"): void {
  form.value.requireText = mode === "link";
  form.value.minFiles = mode === "file" ? 1 : 0;
  form.value.maxFiles = mode === "link" ? 0 : 1;
}

async function load(): Promise<void> {
  editorValid.value = true;
  if (isNew.value) {
    step.value = null;
    form.value = newStepForm();
    showTypePicker.value = !hasChosenType.value;
    return;
  }
  showTypePicker.value = false;
  loading.value = true;
  error.value = "";
  try {
    step.value = await stepApi.step(stepId.value);
    form.value = formFromStep(step.value);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}

function setType(type: StepType): void {
  form.value = newStepForm(type);
  editorValid.value = true;
  hasChosenType.value = true;
  showTypePicker.value = false;
}
async function cancelTypePicker(): Promise<void> {
  showTypePicker.value = false;
  if (!hasChosenType.value) await router.push(backRoute.value);
}
function addOption(): void {
  form.value.options.push({ id: crypto.randomUUID(), text: "", correct: false });
}
function setCorrect(index: number): void {
  if (form.value.type === "single_choice")
    form.value.options.forEach((option, i) => (option.correct = i === index));
  else form.value.options[index]!.correct = !form.value.options[index]!.correct;
}

async function addReferenceFiles(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const files = [...(input.files ?? [])];
  input.value = "";
  if (!files.length) return;
  uploading.value = true;
  error.value = "";
  try {
    for (const file of files) form.value.referenceFiles.push(await uploadAnswerFile(file));
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    uploading.value = false;
  }
}

async function addTestFile(
  event: Event,
  test: CodeSample,
  field: "input_file" | "output_file",
): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  uploading.value = true;
  error.value = "";
  try {
    test[field] = await uploadAnswerFile(file);
    if (field === "input_file") test.input = "";
    else test.output = "";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    uploading.value = false;
  }
}

async function save(): Promise<void> {
  if (uploading.value || imageUploading.value) {
    error.value = "Дождитесь завершения загрузки файла.";
    return;
  }
  if (!editorValid.value) {
    error.value = "Исправьте содержимое шага в редакторе перед сохранением.";
    return;
  }
  error.value = validateStepForm(form.value) ?? "";
  success.value = "";
  if (error.value) return;
  saving.value = true;
  try {
    const data = {
      payload: payloadFromForm(form.value),
      comment: comment.value.trim() || undefined,
      is_breaking: isBreaking.value,
      base_revision: step.value?.revision.number,
    };
    const saved = isNew.value
      ? await stepApi.createStep(Number(route.params.moduleId), data)
      : await stepApi.saveStep(stepId.value, data);
    if (isNew.value) {
      await router.replace({
        name: ADMIN_STEP_ROUTE.name,
        params: { stepId: saved.id },
        query: route.query,
      });
    }
    step.value = saved;
    form.value = formFromStep(saved);
    comment.value = "";
    isBreaking.value = false;
    success.value = `Редакция ${saved.revision.number} сохранена`;
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
watch(
  () => route.fullPath,
  (next, previous) => {
    if (next !== previous) {
      if (isNew.value) hasChosenType.value = false;
      load();
    }
  },
);
</script>

<template>
  <div class="admin-page admin-page--detail">
    <Teleport to="#admin-page-header">
    <div class="admin-toolbar admin-toolbar--detail">
      <div>
        <RouterLink class="admin-link" :to="backRoute">← К курсу</RouterLink>
        <h2>{{ isNew ? "Новый шаг" : `Шаг #${stepId}` }}</h2>
        <p v-if="step">
          Редакция {{ step.revision.number }} ·
          {{ step.is_hidden ? "Скрыт от учеников" : "Виден ученикам" }}
        </p>
      </div>
      <div class="admin-actions">
        <span class="admin-badge">{{ stepTypeLabels[form.type] }}</span>
        <button v-if="isNew" class="admin-button" type="button" @click="showTypePicker = true">Сменить тип</button>
        <RouterLink
          v-if="step"
          class="admin-button"
          :to="{ name: ADMIN_REVISIONS_ROUTE.name, params: { stepId }, query: route.query }"
          >История редакций</RouterLink
        ><button
          class="admin-button admin-button--primary"
          type="button"
          :disabled="saving || loading || uploading || imageUploading"
          @click="save"
        >
          {{ saving ? "Сохраняем…" : isNew ? "Создать шаг" : "Сохранить редакцию" }}
        </button>
      </div>
    </div>
    </Teleport>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="success" class="admin-success" role="status">{{ success }}</p>
    <p v-if="uploading" class="admin-note" role="status">Загружаем файл…</p>
    <div v-if="loading" class="admin-panel admin-empty">Загружаем шаг…</div>
    <StepTypePicker v-if="showTypePicker && isNew" :module-label="String(route.query.moduleTitle ?? '')" @choose="setType" @cancel="cancelTypePicker" />
    <template v-else>
      <div class="admin-grid admin-grid--wide step-editor-layout">
        <div class="admin-stack">
          <div class="step-head-fields">
          <label class="admin-field step-title-field">Название
            <input v-model="form.title" maxlength="200" placeholder="Название шага" />
          </label>
          <template v-if="form.type === 'programming'">
            <label class="admin-field step-limit-field">Время, мс<input v-model.number="form.timeLimitMs" type="number" min="100" max="15000" /></label>
            <label class="admin-field step-limit-field">Память, МБ<input v-model.number="form.memoryLimitMb" type="number" min="16" max="512" /></label>
          </template>
          </div>
          <section class="step-main-field">
            <div class="admin-field">
              <span>{{ form.type === "theory" ? "Текст" : form.type === "programming" ? "Условие" : form.type === "single_choice" || form.type === "multiple_choice" ? "Вопрос" : "Задание" }}</span
              ><RichTextEditor
                :key="`${step?.id ?? 'new'}-${step?.revision.number ?? form.type}`"
                v-model="form.body"
                @error="error = $event"
                @validity="editorValid = $event"
                @uploading="imageUploading = $event"
              />
            </div>
          </section>
          <section
            v-if="form.type === 'single_choice' || form.type === 'multiple_choice'"
            class="admin-panel step-answer-section"
          >
            <div class="admin-panel-head">
              <div>
                <h2>Варианты ответа</h2>
                <p>
                  {{
                    form.type === "single_choice"
                      ? "Отметьте один верный ответ."
                      : "Отметьте все верные ответы."
                  }}
                </p>
              </div>
            </div>
            <div class="answer-format">
              <span class="admin-section-label">Формат ответа</span>
              <div class="answer-format-tabs" role="group" aria-label="Формат ответа">
                <button type="button" :class="{ active: form.type === 'single_choice' }" :disabled="!isNew && form.type !== 'single_choice'" @click="form.type = 'single_choice'; form.options.forEach((option, index) => option.correct = index === 0)">Один верный</button>
                <button type="button" :class="{ active: form.type === 'multiple_choice' }" :disabled="!isNew && form.type !== 'multiple_choice'" @click="form.type = 'multiple_choice'">Несколько верных</button>
              </div>
            </div>
            <div class="admin-stack choice-list">
              <div v-for="(option, index) in form.options" :key="option.id" class="choice-row">
                <input
                  :type="form.type === 'single_choice' ? 'radio' : 'checkbox'"
                  :name="form.type === 'single_choice' ? 'correct-option' : undefined"
                  :checked="option.correct"
                  :aria-label="`Верный ответ ${index + 1}`"
                  @change="setCorrect(index)"
                /><input
                  v-model="option.text"
                  class="admin-input"
                  :aria-label="`Текст варианта ${index + 1}`"
                  :placeholder="`Вариант ${index + 1}`"
                /><button
                  class="admin-button"
                  type="button"
                  :disabled="form.options.length <= 2"
                  :aria-label="`Удалить вариант ${index + 1}`"
                  @click="form.options.splice(index, 1)"
                >
                  ×
                </button>
              </div>
            </div>
            <button
              class="admin-button admin-button--subtle"
              style="margin-top: 16px"
              type="button"
              :disabled="form.options.length >= 50"
              @click="addOption"
            >
              + Вариант
            </button>
          </section>
          <section v-if="form.type === 'free_text'" class="admin-panel step-answer-section">
            <div class="admin-panel-head">
              <div>
                <h2>Формат ответа</h2>
                <p>Текст и вложения ученика.</p>
              </div>
            </div>
            <div class="answer-format-tabs" role="group" aria-label="Что сдаёт ученик">
              <button type="button" :class="{ active: submissionMode === 'link' }" @click="setSubmissionMode('link')">Ссылка</button>
              <button type="button" :class="{ active: submissionMode === 'file' }" @click="setSubmissionMode('file')">Файл</button>
              <button type="button" :class="{ active: submissionMode === 'either' }" @click="setSubmissionMode('either')">Ссылка или файл</button>
            </div>
            <div class="admin-form">
              <label class="admin-check"
                ><input v-model="form.requireText" type="checkbox" /> Требовать текстовый
                ответ</label
              >
              <div class="admin-form-row">
                <label class="admin-field"
                  >Минимум файлов<input
                    v-model.number="form.minFiles"
                    type="number"
                    min="0"
                    max="10" /></label
                ><label class="admin-field"
                  >Максимум файлов<input
                    v-model.number="form.maxFiles"
                    type="number"
                    min="0"
                    max="10"
                /></label>
              </div>
              <label class="admin-field"
                >Эталон ответа (для куратора)<textarea v-model="form.reference" rows="4" /></label
              ><label class="admin-field"
                >Критерии проверки<textarea v-model="form.criteria" rows="4" />
              </label>
              <label class="admin-field"
                >Допустимые MIME-типы файлов<input
                  v-model="form.allowedMime"
                  placeholder="image/png, image/jpeg (пусто — любые)"
              /></label>
              <label class="admin-field"
                >Эталонные файлы для куратора<input
                  type="file"
                  multiple
                  :disabled="uploading"
                  @change="addReferenceFiles"
              /></label>
              <div v-if="form.referenceFiles.length" class="admin-list">
                <div v-for="fileId in form.referenceFiles" :key="fileId" class="admin-list-item">
                  <span>Файл #{{ fileId }}</span
                  ><button
                    class="admin-button"
                    type="button"
                    @click="form.referenceFiles = form.referenceFiles.filter((id) => id !== fileId)"
                  >
                    Убрать
                  </button>
                </div>
              </div>
            </div>
          </section>
          <section v-if="form.type === 'programming'" class="admin-panel">
            <div class="admin-panel-head">
              <div>
                <h2>Код и ограничения</h2>
                <p>Поддерживается Python 3.</p>
              </div>
            </div>
            <div class="admin-form">
              <label class="admin-field"
                >Шаблон кода<textarea
                  v-model="form.template"
                  rows="5"
                  class="code-textarea"
                /></label
              ><label class="admin-field"
                >Эталонное решение (видно только проверяющим)<textarea
                  v-model="form.referenceSolution"
                  rows="5"
                  class="code-textarea"
                />
              </label>
            </div>
          </section>
          <section v-if="form.type === 'programming'" class="admin-panel">
            <div class="admin-panel-head">
              <div>
                <h2>Примеры для ученика</h2>
                <p>Примеры видны ученику и не влияют на баллы.</p>
              </div>
              <button
                class="admin-button admin-button--subtle"
                type="button"
                :disabled="form.samples.length >= 20"
                @click="form.samples.push({ input: '', output: '' })"
              >
                + Пример
              </button>
            </div>
            <div v-if="!form.samples.length" class="admin-empty">Примеры не добавлены</div>
            <div v-for="(sample, index) in form.samples" :key="index" class="test-pair">
              <label class="admin-field"
                >Входные данные<textarea
                  v-model="sample.input"
                  rows="3"
                  class="code-textarea"
                /></label
              ><label class="admin-field"
                >Ожидаемый вывод<textarea
                  v-model="sample.output"
                  rows="3"
                  class="code-textarea"
                /></label
              ><button class="admin-button" type="button" @click="form.samples.splice(index, 1)">
                Убрать
              </button>
            </div>
          </section>
          <section v-if="form.type === 'programming'" class="admin-panel">
            <div class="admin-panel-head">
              <div>
                <h2>Скрытые тесты</h2>
                <p>Вход и ожидаемый вывод никогда не показываются ученику.</p>
              </div>
              <button
                class="admin-button admin-button--subtle"
                type="button"
                :disabled="form.testGroups.length >= 50"
                @click="
                  form.testGroups.push({ name: '', points: 0, tests: [{ input: '', output: '' }] })
                "
              >
                + Группа
              </button>
            </div>
            <div v-if="!form.testGroups.length" class="admin-empty">Групп тестов нет</div>
            <div
              v-for="(group, groupIndex) in form.testGroups"
              :key="groupIndex"
              class="test-group"
            >
              <div class="admin-form-row">
                <label class="admin-field"
                  >Название группы<input v-model="group.name" maxlength="200" /></label
                ><label class="admin-field"
                  >Баллы группы<input v-model.number="group.points" type="number" min="0"
                /></label>
              </div>
              <div v-for="(test, testIndex) in group.tests" :key="testIndex" class="test-pair">
                <label class="admin-field"
                  >Вход <span v-if="test.input_file">(файл #{{ test.input_file }})</span
                  ><textarea
                    v-model="test.input"
                    rows="3"
                    class="code-textarea"
                    :disabled="!!test.input_file"
                  /></label
                ><label class="admin-field"
                  >Ожидаемый вывод
                  <span v-if="test.output_file">(файл #{{ test.output_file }})</span
                  ><textarea
                    v-model="test.output"
                    rows="3"
                    class="code-textarea"
                    :disabled="!!test.output_file"
                  /></label
                ><button
                  class="admin-button"
                  type="button"
                  @click="group.tests.splice(testIndex, 1)"
                >
                  Убрать тест
                </button>
                <div
                  v-if="test.input_file || test.output_file"
                  class="admin-actions"
                  style="grid-column: 1 / -1"
                >
                  <button
                    v-if="test.input_file"
                    class="admin-button"
                    type="button"
                    @click="test.input_file = null"
                  >
                    Убрать файл входа</button
                  ><button
                    v-if="test.output_file"
                    class="admin-button"
                    type="button"
                    @click="test.output_file = null"
                  >
                    Убрать файл вывода
                  </button>
                </div>
                <div class="admin-form-row" style="grid-column: 1 / -1">
                  <label class="admin-field"
                    >Загрузить входной файл<input
                      type="file"
                      :disabled="uploading"
                      @change="addTestFile($event, test, 'input_file')" /></label
                  ><label class="admin-field"
                    >Загрузить файл с ответом<input
                      type="file"
                      :disabled="uploading"
                      @change="addTestFile($event, test, 'output_file')"
                  /></label>
                </div>
              </div>
              <div class="admin-actions">
                <button
                  class="admin-button"
                  type="button"
                  :disabled="group.tests.length >= 200"
                  @click="group.tests.push({ input: '', output: '' })"
                >
                  + Тест</button
                ><button
                  class="admin-button admin-button--danger"
                  type="button"
                  @click="form.testGroups.splice(groupIndex, 1)"
                >
                  Удалить группу
                </button>
              </div>
            </div>
          </section>
        </div>
        <div class="admin-stack step-settings-rail">
          <section class="admin-panel">
            <div class="admin-panel-head">
              <div>
                <h2>Проверка и баллы</h2>
                <p>Параметры попыток и оценки.</p>
              </div>
            </div>
            <div class="admin-form">
              <div class="step-grading-mode">{{ form.type === 'theory' ? 'При прочтении' : form.type === 'free_text' ? 'Куратор' : form.type === 'programming' && form.grading === 'manual' ? 'Куратор' : 'Авто' }}</div>
              <label v-if="form.type !== 'theory'" class="admin-field"
                >Максимальный балл<input
                  v-model.number="form.maxScore"
                  type="number"
                  min="0"
                  max="1000"
              /></label>
              <p v-else class="admin-note">Теория не оценивается в баллах.</p>
              <label v-if="form.type !== 'theory'" class="admin-field"
                >Максимум попыток<input
                  v-model.number="form.maxAttempts"
                  type="number"
                  min="1"
                  placeholder="Без ограничения"
                /><small>Оставьте пустым для неограниченного числа попыток.</small></label
              ><label v-if="form.type !== 'theory'" class="admin-field"
                >Когда показывать ответ<select v-model="form.showAnswer">
                  <option value="never">Никогда</option>
                  <option value="after_wrong">После неверной попытки</option>
                  <option value="after_attempts_exhausted">После исчерпания попыток</option>
                  <option value="after_solved">После решения</option>
                </select></label
              ><label v-if="form.type === 'multiple_choice'" class="admin-field"
                >Начисление баллов<select v-model="form.scoring">
                  <option value="all_or_nothing">Всё или ничего</option>
                  <option value="partial">Частичный балл</option>
                </select></label
              ><template v-if="form.type === 'programming'"
                ><label class="admin-field"
                  >Способ проверки<select v-model="form.grading">
                    <option value="tests">Автотесты</option>
                    <option value="tests_and_review">Тесты и куратор</option>
                    <option value="manual">Только куратор</option>
                  </select></label
                ><label class="admin-field"
                  >Начисление баллов<select v-model="form.scoring">
                    <option value="all_or_nothing">Всё или ничего</option>
                    <option value="per_group">За группы тестов</option>
                  </select></label
              ></template
              >
              <label class="admin-check"><input type="checkbox" checked disabled /> Обязательный</label>
            </div>
          </section>
          <section class="admin-panel">
            <div class="admin-panel-head"><div><h2>Навыки на карте</h2></div></div>
            <p class="admin-muted">Привязка навыков к шагу появится после добавления этого поля в API.</p>
          </section>
          <section class="admin-panel">
            <div class="admin-panel-head"><div><h2>Место в курсе</h2></div></div>
            <div class="admin-field"><span>Модуль</span><div class="step-module-name">{{ route.query.moduleTitle || `Модуль #${route.params.moduleId || step?.module_id || '—'}` }}</div></div>
            <p class="admin-muted">Порядок шага можно изменить в конструкторе курса.</p>
          </section>
          <section v-if="!isNew" class="admin-panel">
            <div class="admin-panel-head">
              <div>
                <h2>Новая редакция</h2>
                <p>Предыдущие редакции сохраняются в истории.</p>
              </div>
            </div>
            <div class="admin-form">
              <label class="admin-field"
                >Комментарий к изменению<input
                  v-model="comment"
                  maxlength="1000"
                  placeholder="Что изменилось" /></label
              ><label class="admin-check"
                ><input v-model="isBreaking" type="checkbox" /> Существенное изменение ответа</label
              >
              <p class="admin-note">
                Отметьте, если правильный ответ или тесты изменились: старые решения будут помечены
                устаревшими.
              </p>
            </div>
          </section>
          <div class="admin-actions">
            <button
              class="admin-button admin-button--primary"
              type="button"
              :disabled="saving || uploading || imageUploading"
              @click="save"
            >
              {{ saving ? "Сохраняем…" : isNew ? "Создать шаг" : "Сохранить редакцию" }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.step-title-field { font-size: 13px; }
.step-head-fields { display: flex; align-items: end; gap: 12px; }
.step-head-fields .step-title-field { flex: 1; }
.step-limit-field { width: 105px; }
.step-main-field .admin-field { font-size: 13px; }
.step-answer-section { padding: 0; border: 0; background: transparent; }
.step-answer-section .admin-panel-head { margin-bottom: 12px; }
.step-answer-section .admin-panel-head h2 { font-size: 16px; }
.step-grading-mode { justify-self: start; padding: 6px 10px; border-radius: 8px; background: #f0f2f6; color: #0f172a; font-size: 12px; font-weight: 650; }
.step-module-name { padding: 10px 12px; border: 1px solid #e1e6f0; border-radius: 8px; background: #f4f6fb; color: #4a546b; font-size: 13px; }
.step-editor-layout { gap: 20px; }
.step-settings-rail { position: sticky; top: 0; }
.choice-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: 1px solid #e1e6f0;
  border-radius: 11px;
  background: #fafbfe;
}
.answer-format { display: grid; gap: 8px; margin-bottom: 16px; }
.answer-format-tabs { display: inline-flex; flex-wrap: wrap; gap: 2px; width: max-content; max-width: 100%; padding: 3px; border-radius: 10px; background: #f0f2f6; }
.answer-format-tabs button { min-height: 32px; padding: 0 11px; border: 0; border-radius: 8px; background: transparent; color: #4a546b; font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; }
.answer-format-tabs button.active { background: #fff; color: #0f172a; box-shadow: 0 1px 2px #0f172a14; }
.answer-format-tabs button:disabled:not(.active) { opacity: .45; cursor: not-allowed; }
.choice-row:has(input:checked) { border-color: #b8ddca; background: #f1faf5; }
.choice-row > input:first-child {
  flex: none;
  accent-color: #17915a;
}
.code-textarea {
  font-family: "SFMono-Regular", Consolas, monospace !important;
}
.test-group {
  display: grid;
  gap: 14px;
  margin-top: 14px;
  padding: 16px;
  border: 1px solid #e6ebf3;
  border-radius: 11px;
}
.test-pair {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  align-items: end;
  gap: 10px;
  margin-top: 12px;
}
@media (max-width: 650px) {
  .test-pair {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) { .step-settings-rail { position: static; } }
</style>
