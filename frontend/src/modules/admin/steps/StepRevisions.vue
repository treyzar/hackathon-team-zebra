<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { stepApi } from "./api";
import RichTextEditor from "./RichTextEditor.vue";
import { formatDate, stepTypeLabels } from "../shared/format";
import type { Revision, RevisionSummary, RichText, Step } from "../shared/types";
import { ADMIN_COURSE_ROUTE } from "@/pages/admin/course/constants";
import { ADMIN_STEP_ROUTE } from "@/pages/admin/step/constants";

const route = useRoute();
const stepId = Number(route.params.stepId);
const courseId = Number(route.query.courseId);
const step = ref<Step | null>(null);
const revisions = ref<RevisionSummary[]>([]);
const selected = ref<Revision | null>(null);
const loading = ref(true);
const error = ref("");
const selectedSummary = computed(() =>
  revisions.value.find((item) => item.number === selected.value?.number),
);
const contentDoc = computed<RichText | null>(() => {
  const content = selected.value?.content;
  const value = content?.body ?? content?.question ?? content?.statement;
  return value && typeof value === "object" && (value as RichText).type === "doc"
    ? (value as RichText)
    : null;
});

async function select(number: number): Promise<void> {
  error.value = "";
  try {
    selected.value = await stepApi.revision(stepId, number);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  }
}
async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    [step.value, revisions.value] = await Promise.all([
      stepApi.step(stepId),
      stepApi.revisions(stepId),
    ]);
    if (revisions.value.length) await select(revisions.value[0]!.number);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<template>
  <div class="admin-page admin-page--detail">
    <Teleport to="#admin-page-header">
      <div class="admin-toolbar admin-toolbar--detail">
        <div>
          <RouterLink
            class="admin-link"
            :to="
              Number.isInteger(courseId) && courseId > 0
                ? { name: ADMIN_COURSE_ROUTE.name, params: { courseId } }
                : { name: ADMIN_STEP_ROUTE.name, params: { stepId } }
            "
            >← Назад</RouterLink
          >
          <h2>{{ step ? stepTypeLabels[step.type] : "Шаг" }} #{{ stepId }}</h2>
          <p>{{ revisions.length }} редакций сохранено</p>
        </div>
        <RouterLink
          class="admin-button admin-button--primary"
          :to="{ name: ADMIN_STEP_ROUTE.name, params: { stepId }, query: route.query }"
          >Редактировать шаг</RouterLink
        >
      </div>
    </Teleport>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <div v-if="loading" class="admin-panel admin-empty">Загружаем историю…</div>
    <div v-else class="admin-grid admin-grid--wide">
      <section class="admin-panel">
        <div class="admin-panel-head">
          <div>
            <h2>Редакции</h2>
            <p>Каждое сохранение задания создаёт новую запись.</p>
          </div>
        </div>
        <div v-if="!revisions.length" class="admin-empty">История пока пуста</div>
        <div v-else class="admin-list">
          <button
            v-for="revision in revisions"
            :key="revision.number"
            class="revision-item"
            :class="{ 'revision-item--active': selected?.number === revision.number }"
            type="button"
            @click="select(revision.number)"
          >
            <span class="admin-badge">№ {{ revision.number }}</span
            ><span
              ><strong>{{ revision.comment || "Без комментария" }}</strong
              ><small
                >{{ formatDate(revision.created_at) }} · Автор #{{
                  revision.author_id ?? "—"
                }}</small
              ></span
            ><span v-if="revision.is_breaking" class="admin-badge admin-badge--orange"
              >Существенная</span
            >
          </button>
        </div>
      </section>
      <section v-if="selected" class="admin-panel">
        <div class="admin-panel-head">
          <div>
            <h2>Редакция {{ selected.number }}</h2>
            <p>{{ selectedSummary ? formatDate(selectedSummary.created_at) : "" }}</p>
          </div>
        </div>
        <div class="admin-stack">
          <div class="revision-fact">
            <span>Максимальный балл</span><strong>{{ selected.max_score }}</strong>
          </div>
          <div class="revision-fact">
            <span>Проверка</span><strong>{{ selected.settings.grading }}</strong>
          </div>
          <div class="revision-fact">
            <span>Номер схемы</span><strong>{{ selected.schema_version }}</strong>
          </div>
          <div class="revision-fact">
            <span>Существенное изменение</span
            ><strong>{{ selected.is_breaking ? "Да" : "Нет" }}</strong>
          </div>
        </div>
        <div v-if="contentDoc" style="margin-top: 22px">
          <h2 style="margin-bottom: 11px">Содержание</h2>
          <RichTextEditor
            :key="selected.number"
            :model-value="contentDoc"
            readonly
            @error="error = $event"
          />
        </div>
        <p class="admin-note" style="margin-top: 18px">
          Редакции неизменяемы. Для правки откройте текущий шаг и сохраните новую редакцию.
        </p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.revision-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 13px;
  border: 1px solid #e4eaf3;
  border-radius: 10px;
  background: #fff;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.revision-item--active {
  border-color: #3457f0;
  background: #f6f8ff;
}
.revision-item > span:nth-child(2) {
  flex: 1;
  min-width: 0;
}
.revision-item strong {
  display: block;
  color: #1d2b43;
  font-size: 12px;
}
.revision-item small {
  display: block;
  margin-top: 4px;
  color: #8793a6;
  font-size: 11px;
}
.revision-fact {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 11px;
  border-bottom: 1px solid #edf1f7;
  font-size: 12px;
}
.revision-fact span {
  color: #7e8aa0;
}
.revision-fact strong {
  color: #20304b;
}
</style>
