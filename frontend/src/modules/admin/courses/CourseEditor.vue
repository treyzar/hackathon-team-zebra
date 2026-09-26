<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { courseApi } from "./api";
import { reorderIds } from "./reorder";
import CourseStepWorkbench from "./CourseStepWorkbench.vue";
import { stepApi } from "../steps/api";
import { docToText, stepTypeLabels, textToDoc } from "../shared/format";
import type { CourseTree, Module, StepAccess, StepSummary } from "../shared/types";
import { ADMIN_COURSES_ROUTE } from "@/pages/admin/courses/constants";
import { ADMIN_PUBLISH_ROUTE } from "@/pages/admin/publish/constants";
import { ADMIN_IMPORT_ROUTE } from "@/pages/admin/import/constants";
import { ADMIN_STEP_NEW_ROUTE } from "@/pages/admin/step/constants";

const route = useRoute();
const router = useRouter();
const courseId = computed(() => Number(route.params.courseId));
const course = ref<CourseTree | null>(null);
const stepTitles = ref<Record<number, string>>({});
const loading = ref(true);
const busy = ref(false);
const error = ref("");
const success = ref("");
const tab = ref<"structure" | "passport">("structure");
const title = ref("");
const slug = ref("");
const description = ref("");
const stepAccess = ref<StepAccess>("all");
const newModuleTitle = ref("");
const renamingId = ref<number | null>(null);
const renameValue = ref("");
type DragItem = { kind: "module"; id: number } | { kind: "step"; moduleId: number; id: number };
const dragging = ref<DragItem | null>(null);
const dropTarget = ref<DragItem | null>(null);
const dropAfter = ref(false);
const stepCount = computed(
  () => course.value?.modules.reduce((sum, module) => sum + module.steps.length, 0) ?? 0,
);
const selectedStepId = ref<number | null>(null);
// The step editor comes back here with ?added=<id> after creating a step.
const addedStep = computed(() => {
  const id = Number(route.query.added);
  for (const [index, module] of (course.value?.modules ?? []).entries()) {
    const step = module.steps.find((item) => item.id === id);
    if (step) return { step, module, number: index + 1 };
  }
  return null;
});
const selectedStep = computed(() => {
  for (const module of course.value?.modules ?? []) {
    const index = module.steps.findIndex((step) => step.id === selectedStepId.value);
    if (index >= 0) return { module, step: module.steps[index]!, index };
  }
  return null;
});

function syncForm(data: CourseTree): void {
  title.value = data.title;
  slug.value = data.slug;
  description.value = docToText(data.description);
  stepAccess.value = data.step_access;
}

async function loadStepTitles(data: CourseTree): Promise<void> {
  const steps = data.modules.flatMap((module) => module.steps);
  for (let index = 0; index < steps.length; index += 8) {
    const batch = steps.slice(index, index + 8);
    const results = await Promise.allSettled(batch.map((step) => stepApi.step(step.id)));
    const titles: Record<number, string> = {};
    results.forEach((result, position) => {
      if (result.status !== "fulfilled") return;
      const content = result.value.revision.content;
      const body = content.body ?? content.question ?? content.statement;
      const firstLine = docToText(body)
        .split("\n")
        .find((line) => line.trim());
      titles[batch[position]!.id] =
        firstLine?.trim().slice(0, 80) || stepTypeLabels[result.value.type];
    });
    stepTitles.value = { ...stepTitles.value, ...titles };
  }
}

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const data = await courseApi.course(courseId.value);
    course.value = data;
    void loadStepTitles(data);
    const added = Number(route.query.added);
    if (data.modules.some((module) => module.steps.some((step) => step.id === added)))
      selectedStepId.value = added;
    if (
      !data.modules.some((module) => module.steps.some((step) => step.id === selectedStepId.value))
    )
      selectedStepId.value = data.modules.flatMap((module) => module.steps)[0]?.id ?? null;
    syncForm(data);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}

async function saveCourse(): Promise<void> {
  busy.value = true;
  error.value = "";
  success.value = "";
  try {
    await courseApi.updateCourse(courseId.value, {
      title: title.value.trim(),
      slug: slug.value.trim(),
      description: textToDoc(description.value),
      step_access: stepAccess.value,
    });
    await load();
    success.value = "Настройки курса сохранены";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

async function createModule(): Promise<void> {
  if (!newModuleTitle.value.trim()) return;
  busy.value = true;
  error.value = "";
  try {
    await courseApi.createModule(courseId.value, newModuleTitle.value.trim());
    newModuleTitle.value = "";
    await load();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

async function renameModule(id: number): Promise<void> {
  if (!renameValue.value.trim()) return;
  busy.value = true;
  error.value = "";
  try {
    await courseApi.renameModule(id, renameValue.value.trim());
    renamingId.value = null;
    await load();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

function startDrag(event: DragEvent, item: DragItem): void {
  if (busy.value || !event.dataTransfer) {
    event.preventDefault();
    return;
  }
  dragging.value = item;
  dropTarget.value = null;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", String(item.id));
}

function canDrop(target: DragItem): boolean {
  const source = dragging.value;
  return (
    !!source &&
    source.kind === target.kind &&
    (source.kind === "module" || (target.kind === "step" && source.moduleId === target.moduleId))
  );
}

function dragOver(event: DragEvent, target: DragItem): void {
  if (!canDrop(target)) return;
  event.preventDefault();
  event.stopPropagation();
  if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
  const element = event.currentTarget as HTMLElement;
  const bounds = element.getBoundingClientRect();
  dropTarget.value = target;
  dropAfter.value = event.clientY > bounds.top + bounds.height / 2;
}

function isDropTarget(target: DragItem, after: boolean): boolean {
  const current = dropTarget.value;
  return (
    !!current &&
    current.kind === target.kind &&
    current.id === target.id &&
    (current.kind === "module" ||
      (target.kind === "step" && current.moduleId === target.moduleId)) &&
    dropAfter.value === after
  );
}

function endDrag(): void {
  dragging.value = null;
  dropTarget.value = null;
}

async function dropModule(event: DragEvent, targetId: number): Promise<void> {
  event.preventDefault();
  event.stopPropagation();
  const source = dragging.value;
  const after = dropAfter.value;
  endDrag();
  if (!course.value || source?.kind !== "module") return;
  const modules = course.value.modules;
  const ids = reorderIds(
    modules.map((item) => item.id),
    source.id,
    targetId,
    after,
  );
  if (ids.every((id, index) => id === modules[index]?.id)) return;
  course.value.modules = ids.map((id) => modules.find((item) => item.id === id)!);
  busy.value = true;
  error.value = "";
  try {
    await courseApi.orderModules(courseId.value, ids);
    await load();
  } catch (cause) {
    await load();
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

async function dropStep(event: DragEvent, module: Module, targetId: number): Promise<void> {
  event.preventDefault();
  event.stopPropagation();
  const source = dragging.value;
  const after = dropAfter.value;
  endDrag();
  if (source?.kind !== "step" || source.moduleId !== module.id) return;
  const steps = module.steps;
  const ids = reorderIds(
    steps.map((item) => item.id),
    source.id,
    targetId,
    after,
  );
  if (ids.every((id, index) => id === steps[index]?.id)) return;
  module.steps = ids.map((id) => steps.find((item) => item.id === id)!);
  busy.value = true;
  error.value = "";
  try {
    await courseApi.orderSteps(module.id, ids);
    await load();
  } catch (cause) {
    await load();
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

async function toggleStep(step: StepSummary): Promise<void> {
  busy.value = true;
  error.value = "";
  try {
    await stepApi.setStepHidden(step.id, !step.is_hidden);
    await load();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

async function deleteCourse(): Promise<void> {
  if (!course.value || !window.confirm(`Удалить курс «${course.value.title}»?`)) return;
  busy.value = true;
  error.value = "";
  try {
    await courseApi.deleteCourse(courseId.value);
    await router.replace(ADMIN_COURSES_ROUTE.path);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

async function deleteModule(module: Module): Promise<void> {
  if (!window.confirm(`Удалить модуль «${module.title}» и все его шаги?`)) return;
  busy.value = true;
  error.value = "";
  try {
    await courseApi.deleteModule(module.id);
    await load();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

async function dismissAdded(): Promise<void> {
  const { added: _added, ...query } = route.query;
  await router.replace({ query });
}

async function deleteStep(step: StepSummary): Promise<void> {
  if (!window.confirm(`Удалить шаг #${step.id}?`)) return;
  if (step.id === addedStep.value?.step.id) await dismissAdded();
  busy.value = true;
  error.value = "";
  try {
    await stepApi.deleteStep(step.id);
    await load();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}

onMounted(load);
watch(courseId, load);
</script>

<template>
  <div
    class="admin-page admin-page--detail"
    :class="{ 'admin-page--course-structure': tab === 'structure' }"
  >
    <Teleport defer to="#admin-page-header">
      <div class="admin-toolbar admin-toolbar--detail">
        <div>
          <p class="admin-breadcrumbs">
            <RouterLink :to="ADMIN_COURSES_ROUTE.path">Курсы</RouterLink> ›
            {{ course?.title ?? "Курс" }}
          </p>
          <h2>Конструктор курса</h2>
        </div>
        <div class="admin-actions">
          <span
            v-if="course"
            class="admin-badge"
            :class="course.is_published ? 'admin-badge--green' : 'admin-badge--gray'"
            >{{ course.is_published ? "Опубликован" : "Черновик" }}</span
          ><button
            class="admin-button"
            type="button"
            @click="tab = tab === 'structure' ? 'passport' : 'structure'"
          >
            {{ tab === "structure" ? "Настройки" : "К структуре" }}</button
          >
          <RouterLink class="admin-button" :to="ADMIN_IMPORT_ROUTE.path"
            >Импорт / экспорт</RouterLink
          >
          <RouterLink
            v-if="course"
            class="admin-button admin-button--primary"
            :to="{ name: ADMIN_PUBLISH_ROUTE.name, params: { courseId } }"
            >Публикация →</RouterLink
          >
        </div>
      </div>
    </Teleport>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="success" class="admin-success" role="status">{{ success }}</p>
    <div v-if="addedStep && tab === 'structure'" class="course-added" role="status">
      <strong
        >✓ Шаг «{{ stepTitles[addedStep.step.id] || stepTypeLabels[addedStep.step.type] }}» добавлен
        в модуль {{ addedStep.number }}</strong
      >
      <span v-if="course?.is_published && !addedStep.step.is_hidden">и уже виден ученикам</span>
      <span class="course-added-spacer" />
      <RouterLink
        class="course-added-action"
        :to="{
          name: ADMIN_STEP_NEW_ROUTE.name,
          params: { moduleId: addedStep.module.id },
          query: { courseId, moduleTitle: addedStep.module.title },
        }"
        >+ Добавить ещё шаг</RouterLink
      >
      <button
        class="course-added-action"
        type="button"
        :disabled="busy"
        @click="deleteStep(addedStep.step)"
      >
        Отменить
      </button>
      <button class="course-added-close" type="button" aria-label="Скрыть" @click="dismissAdded">
        ×
      </button>
    </div>
    <div v-if="loading" class="admin-panel admin-empty">Загружаем курс…</div>
    <template v-else-if="course">
      <template v-if="tab === 'structure'">
        <div class="course-editor-layout">
          <section class="course-editor-sidebar" aria-label="Структура курса">
            <div class="course-sidebar-heading">
              <div>
                <h2>Структура курса</h2>
                <p>{{ course.modules.length }} модулей · {{ stepCount }} шагов</p>
              </div>
            </div>
            <div
              class="course-sidebar-scroll"
              role="region"
              aria-label="Модули и шаги"
              tabindex="0"
            >
              <div v-if="!course.modules.length" class="admin-empty">
                Модулей пока нет. Добавьте первый модуль ниже.
              </div>
              <div v-else class="admin-stack">
                <article
                  v-for="(module, moduleIndex) in course.modules"
                  :key="module.id"
                  class="admin-panel course-module"
                >
                  <div
                    class="admin-panel-head course-module-head"
                    :class="{
                      'course-drop-before': isDropTarget({ kind: 'module', id: module.id }, false),
                      'course-drop-after': isDropTarget({ kind: 'module', id: module.id }, true),
                    }"
                    @dragover="dragOver($event, { kind: 'module', id: module.id })"
                    @drop="dropModule($event, module.id)"
                  >
                    <div v-if="renamingId !== module.id" class="course-module-title">
                      <button
                        class="course-drag-handle"
                        type="button"
                        draggable="true"
                        :disabled="busy"
                        :aria-label="`Перетащить модуль ${module.title}`"
                        @dragstart="startDrag($event, { kind: 'module', id: module.id })"
                        @dragend="endDrag"
                      >
                        ⋮⋮
                      </button>
                      <span class="admin-number"
                        >{{ moduleIndex + 1 }}. {{ module.title.toUpperCase() }}</span
                      >
                      <small>{{ module.steps.length }} шагов</small>
                    </div>
                    <form v-else class="admin-actions" @submit.prevent="renameModule(module.id)">
                      <input
                        v-model="renameValue"
                        class="admin-input"
                        maxlength="200"
                        required
                        aria-label="Название модуля"
                      /><button class="admin-button admin-button--primary" :disabled="busy">
                        Сохранить</button
                      ><button class="admin-button" type="button" @click="renamingId = null">
                        Отмена
                      </button>
                    </form>
                    <div v-if="renamingId !== module.id" class="admin-actions">
                      <button
                        class="admin-button"
                        type="button"
                        @click="
                          renamingId = module.id;
                          renameValue = module.title;
                        "
                      >
                        Переименовать</button
                      ><button
                        class="admin-button admin-button--danger"
                        type="button"
                        :disabled="busy"
                        @click="deleteModule(module)"
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                  <div v-if="!module.steps.length" class="admin-empty">В модуле пока нет шагов</div>
                  <div v-else class="admin-list">
                    <div
                      v-for="(step, stepIndex) in module.steps"
                      :key="step.id"
                      class="admin-list-item course-step-row"
                      :class="{
                        'course-step-row--selected': selectedStepId === step.id,
                        'course-step-row--added': addedStep?.step.id === step.id,
                        'course-drop-before': isDropTarget(
                          { kind: 'step', moduleId: module.id, id: step.id },
                          false,
                        ),
                        'course-drop-after': isDropTarget(
                          { kind: 'step', moduleId: module.id, id: step.id },
                          true,
                        ),
                      }"
                      @dragover="
                        dragOver($event, { kind: 'step', moduleId: module.id, id: step.id })
                      "
                      @drop="dropStep($event, module, step.id)"
                    >
                      <button
                        class="course-drag-handle"
                        type="button"
                        draggable="true"
                        :disabled="busy"
                        :aria-label="`Перетащить шаг ${stepTitles[step.id] || step.id}`"
                        @dragstart="
                          startDrag($event, { kind: 'step', moduleId: module.id, id: step.id })
                        "
                        @dragend="endDrag"
                      >
                        ⋮⋮
                      </button>
                      <button
                        class="course-step-select"
                        type="button"
                        :aria-pressed="selectedStepId === step.id"
                        @click="selectedStepId = step.id"
                      >
                        <span class="course-step-type">{{ stepTypeLabels[step.type] }}</span>
                        <span class="course-step-name">{{
                          stepTitles[step.id] || `Шаг ${moduleIndex + 1}.${stepIndex + 1}`
                        }}</span>
                        <small v-if="step.is_hidden" class="course-step-hidden">Скрыт</small>
                        <small v-if="addedStep?.step.id === step.id" class="course-step-new"
                          >НОВЫЙ</small
                        >
                      </button>
                      <details class="course-step-menu">
                        <summary :aria-label="`Действия для шага ${step.id}`">⋯</summary>
                        <div class="course-step-menu-items">
                          <button type="button" :disabled="busy" @click="toggleStep(step)">
                            {{ step.is_hidden ? "Показать" : "Скрыть" }}
                          </button>
                          <button type="button" :disabled="busy" @click="deleteStep(step)">
                            Удалить
                          </button>
                        </div>
                      </details>
                    </div>
                  </div>
                  <RouterLink
                    class="course-add-step-row"
                    :to="{
                      name: ADMIN_STEP_NEW_ROUTE.name,
                      params: { moduleId: module.id },
                      query: { courseId, moduleTitle: module.title },
                    }"
                    >+ Шаг в модуль {{ moduleIndex + 1 }}</RouterLink
                  >
                </article>
              </div>
            </div>
            <div class="course-module-add">
              <h2>Добавить модуль</h2>
              <form @submit.prevent="createModule">
                <input
                  v-model="newModuleTitle"
                  class="admin-input"
                  maxlength="200"
                  required
                  placeholder="Название модуля"
                  aria-label="Название нового модуля"
                />
                <button class="admin-button admin-button--primary" :disabled="busy">
                  Добавить
                </button>
              </form>
            </div>
          </section>
          <aside class="course-editor-preview" aria-label="Редактор выбранного шага">
            <CourseStepWorkbench
              v-if="selectedStep"
              :step-id="selectedStep.step.id"
              :course-id="courseId"
              :number="`${course.modules.indexOf(selectedStep.module) + 1}.${selectedStep.index + 1}`"
              :module-title="selectedStep.module.title"
              @saved="load"
            />
            <section v-else class="admin-panel admin-empty">
              Выберите шаг слева или добавьте новый.
            </section>
          </aside>
        </div>
      </template>
      <section v-else class="admin-panel">
        <div class="admin-panel-head">
          <div>
            <h2>Настройки курса</h2>
            <p>Название, адрес и порядок доступа к шагам.</p>
          </div>
        </div>
        <form class="admin-form" @submit.prevent="saveCourse">
          <div class="admin-form-row">
            <label class="admin-field"
              >Название<input v-model="title" maxlength="200" required /></label
            ><label class="admin-field"
              >Адрес<input v-model="slug" maxlength="100" pattern="[a-z0-9]+(-[a-z0-9]+)*" required
            /></label>
          </div>
          <label class="admin-field">Описание<textarea v-model="description" rows="5" /></label
          ><label class="admin-field"
            >Доступ к шагам<select v-model="stepAccess">
              <option value="all">Все сразу</option>
              <option value="sequential">Последовательно</option>
            </select></label
          >
          <div class="admin-actions">
            <button class="admin-button admin-button--primary" :disabled="busy">
              {{ busy ? "Сохраняем…" : "Сохранить настройки" }}
            </button>
          </div>
        </form>
        <hr class="admin-divider" style="margin: 25px 0" />
        <button
          class="admin-button admin-button--danger"
          type="button"
          :disabled="busy"
          @click="deleteCourse"
        >
          Удалить курс
        </button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.admin-page--course-structure {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.course-editor-layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  flex: 1;
  min-height: 0;
  margin: 0 -32px;
  border-top: 1px solid #e1e6f0;
  border-bottom: 1px solid #e1e6f0;
}
.course-editor-sidebar {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  border-right: 1px solid #e1e6f0;
  background: #fff;
}
.course-sidebar-heading {
  flex: none;
  padding: 20px;
  border-bottom: 1px solid #e1e6f0;
}
.course-sidebar-heading h2,
.course-module-add h2 {
  margin: 0;
  color: #0f172a;
  font-size: 17px;
  letter-spacing: -0.025em;
}
.course-sidebar-heading p {
  margin: 5px 0 0;
  color: #6b7487;
  font-size: 13px;
}
.course-sidebar-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  scrollbar-gutter: stable;
}
.course-sidebar-scroll > .admin-stack {
  gap: 0;
}
.course-sidebar-scroll .course-module {
  padding: 16px 20px;
  border: 0;
  border-top: 1px solid #e1e6f0;
  border-radius: 0;
  box-shadow: none;
}
.course-sidebar-scroll .course-module:first-child {
  border-top: 0;
}
.course-module > .admin-panel-head {
  margin-bottom: 12px;
}
.course-module-add {
  flex: none;
  padding: 16px 20px;
  border-top: 1px solid #e1e6f0;
  background: #fff;
}
.course-module-add form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  margin-top: 10px;
}
.course-module-add .admin-input {
  min-width: 0;
}
.course-editor-layout .admin-list {
  gap: 6px;
}
.course-module-head {
  align-items: center;
}
.course-module-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  min-width: 0;
}
.course-module-title small {
  color: #8992a3;
  font-size: 11px;
}
.course-drag-handle {
  display: grid;
  width: 20px;
  height: 28px;
  flex: none;
  place-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  color: #7c869c;
  font: inherit;
  font-size: 16px;
  letter-spacing: -4px;
  cursor: grab;
  touch-action: none;
}
.course-drag-handle:active {
  cursor: grabbing;
}
.course-drag-handle:disabled {
  cursor: not-allowed;
}
.course-drag-handle:focus-visible {
  outline: 2px solid #3457f0;
  border-radius: 4px;
}
.course-step-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 8px 9px;
  border: 1px solid #e1e6f0;
  border-radius: 12px;
}
.course-step-row--selected {
  border: 2px solid #3457f0;
  padding: 7px 8px;
  background: #eaf0fe;
  font-weight: 600;
}
.course-step-select {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  flex: 1;
  padding: 0;
  border: 0;
  background: none;
  color: #0f172a;
  text-align: left;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.course-step-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.course-step-hidden {
  margin: 0 !important;
  white-space: nowrap;
}
.course-step-type {
  display: inline-flex;
  flex: none;
  padding: 2px 7px;
  border-radius: 6px;
  background: #eaf0fe;
  color: #3457f0;
  font-size: 11px;
  font-weight: 650;
}
.course-step-row--selected .course-step-type {
  background: #fff;
}
.course-step-menu {
  position: relative;
  flex: none;
}
.course-step-menu summary {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 6px;
  color: #7c869c;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  list-style: none;
}
.course-step-menu summary::-webkit-details-marker {
  display: none;
}
.course-step-menu summary:hover {
  background: #f4f6fb;
}
.course-step-menu-items {
  position: absolute;
  z-index: 3;
  bottom: 26px;
  right: 0;
  display: grid;
  min-width: 115px;
  padding: 4px;
  border: 1px solid #e1e6f0;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 24px #0f172a24;
}
.course-step-menu-items button {
  padding: 7px 9px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #26334c;
  text-align: left;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.course-step-menu-items button:hover {
  background: #f4f6fb;
}
.course-add-step-row {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 34px;
  margin-top: 6px;
  border: 1px dashed var(--color-primary-pale);
  border-radius: 10px;
  background: transparent;
  color: #3457f0;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
}
.course-add-step-row:hover {
  background: #eaf0fe;
}
.course-step-row--added,
.course-step-row--added.course-step-row--selected {
  border: 2px solid var(--color-success);
  background: #f3fbf6;
}
.course-step-new {
  color: var(--color-success);
  font-size: 11px;
  font-weight: 700;
}
.course-added {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding: 10px 16px;
  border: 1px solid #bfe3cd;
  border-radius: var(--radius-control);
  background: var(--color-success-soft);
}
.course-added strong {
  color: var(--color-success);
}
.course-added span {
  color: var(--color-muted);
}
.course-added .course-added-spacer {
  flex: 1;
}
.course-added-action {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
}
.course-added-action:hover {
  text-decoration: underline;
}
.course-added-close {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--color-muted);
  font-size: 20px;
  cursor: pointer;
}
.course-added-close:hover {
  background: #d6efe0;
}
.course-drop-before {
  box-shadow: inset 0 3px #3457f0;
}
.course-drop-after {
  box-shadow: inset 0 -3px #3457f0;
}
.course-editor-preview {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
}
.course-editor-preview .admin-panel {
  min-height: 310px;
  padding: 24px;
}
.course-preview-title {
  margin: 8px 0 !important;
  font-size: 24px !important;
}
.course-preview-facts {
  display: grid;
  gap: 1px;
  margin-top: 24px;
  border: 1px solid #e1e6f0;
  border-radius: 12px;
  overflow: hidden;
  background: #e1e6f0;
}
.course-preview-facts > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 15px;
  background: #f8f9fc;
  color: #727d90;
  font-size: 12px;
}
.course-preview-facts strong {
  color: #24324b;
}
@media (max-width: 1050px) {
  .admin-page--course-structure {
    height: auto;
    min-height: 100%;
  }
  .course-editor-layout {
    grid-template-columns: 1fr;
    flex: none;
    min-height: 0;
    margin: 0;
    border: 0;
    gap: 16px;
  }
  .course-editor-sidebar {
    height: min(70dvh, 560px);
    min-height: 320px;
    border: 1px solid #e1e6f0;
    border-radius: 16px;
    overflow: hidden;
  }
  .course-editor-preview {
    overflow: visible;
  }
}
</style>
