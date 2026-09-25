<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { courseApi } from "./api";
import { docToText } from "../shared/format";
import type { CourseTree } from "../shared/types";
import { ADMIN_COURSE_ROUTE } from "@/pages/admin/course/constants";

const route = useRoute();
const courseId = Number(route.params.courseId);
const course = ref<CourseTree | null>(null);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const success = ref("");
const totalSteps = computed(
  () => course.value?.modules.reduce((sum, module) => sum + module.steps.length, 0) ?? 0,
);
const visibleSteps = computed(
  () =>
    course.value?.modules.reduce(
      (sum, module) => sum + module.steps.filter((step) => !step.is_hidden).length,
      0,
    ) ?? 0,
);

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    course.value = await courseApi.course(courseId);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}
async function setPublished(value: boolean): Promise<void> {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await courseApi.updateCourse(courseId, { is_published: value });
    await load();
    success.value = value ? "Курс опубликован" : "Курс снят с публикации";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    saving.value = false;
  }
}
onMounted(load);
</script>

<template>
  <div class="admin-page admin-page--detail">
    <Teleport to="#admin-page-header">
    <div class="admin-toolbar admin-toolbar--detail">
      <div>
        <RouterLink class="admin-link" :to="{ name: ADMIN_COURSE_ROUTE.name, params: { courseId } }"
          >← В конструктор</RouterLink
        >
        <h2>Публикация: {{ course?.title ?? "Курс" }}</h2>
      </div>
      <span
        v-if="course"
        class="admin-badge"
        :class="course.is_published ? 'admin-badge--green' : 'admin-badge--gray'"
        >{{ course.is_published ? "Опубликован" : "Черновик" }}</span
      >
    </div>
    </Teleport>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="success" class="admin-success" role="status">{{ success }}</p>
    <div v-if="loading" class="admin-panel admin-empty">Загружаем курс…</div>
    <template v-else-if="course">
      <div class="publish-grid">
      <div class="publish-main">
      <section class="admin-panel">
        <div class="admin-panel-head">
          <div>
            <h2>Что изменится при публикации</h2>
            <p>Проверьте содержание и доступные шаги.</p>
          </div>
        </div>
        <div class="publish-checks">
          <div>
            <span :class="course.title ? 'check-good' : 'check-warn'">{{
              course.title ? "✓" : "!"
            }}</span>
            <div>
              <strong>Название курса</strong><small>{{ course.title || "Не заполнено" }}</small>
            </div>
          </div>
          <div>
            <span :class="docToText(course.description).trim() ? 'check-good' : 'check-warn'">{{
              docToText(course.description).trim() ? "✓" : "!"
            }}</span>
            <div>
              <strong>Описание</strong
              ><small>{{
                docToText(course.description).trim() ? "Заполнено" : "Описание пока пустое"
              }}</small>
            </div>
          </div>
          <div>
            <span :class="course.modules.length ? 'check-good' : 'check-warn'">{{
              course.modules.length ? "✓" : "!"
            }}</span>
            <div>
              <strong>Модули</strong><small>{{ course.modules.length }} в курсе</small>
            </div>
          </div>
          <div>
            <span :class="visibleSteps ? 'check-good' : 'check-warn'">{{
              visibleSteps ? "✓" : "!"
            }}</span>
            <div>
              <strong>Доступные шаги</strong
              ><small
                >{{ visibleSteps }} видно ученикам · {{ totalSteps - visibleSteps }} скрыто</small
              >
            </div>
          </div>
        </div>
      </section>
      <section class="admin-panel">
        <h2>Содержание курса</h2>
        <div class="publish-modules">
          <div v-for="module in course.modules" :key="module.id"><span class="publish-dot" aria-hidden="true" /><strong>{{ module.title }}</strong><span>{{ module.steps.length }} шагов</span></div>
        </div>
      </section>
      </div>
      <div class="publish-rail">
      <section class="admin-rail-card">
        <div class="admin-panel-head">
          <div>
            <h2>Кого это затронет</h2>
            <p>
              {{
                course.step_access === "all"
                  ? "После публикации все видимые шаги будут доступны сразу."
                  : "После публикации шаги будут открываться последовательно."
              }}
            </p>
          </div>
        </div>
        <p class="admin-note">
          Редакции шагов сохраняются отдельно. Уже отправленные работы остаются связаны с той
          редакцией, на которую ученик отвечал.
        </p>
      </section>
      <section class="admin-rail-card">
        <h2>Публикация курса</h2>
        <div class="admin-actions" style="margin-top: 20px">
          <button
            v-if="!course.is_published"
            class="admin-button admin-button--primary"
            type="button"
            :disabled="saving || !visibleSteps"
            @click="setPublished(true)"
          >
            {{ saving ? "Публикуем…" : "Опубликовать курс" }}</button
          ><button
            v-else
            class="admin-button admin-button--danger"
            type="button"
            :disabled="saving"
            @click="setPublished(false)"
          >
            {{ saving ? "Снимаем…" : "Снять с публикации" }}</button
          ><RouterLink
            class="admin-button"
            :to="{ name: ADMIN_COURSE_ROUTE.name, params: { courseId } }"
            >Вернуться к редактированию</RouterLink
          >
        </div>
        <p v-if="!visibleSteps" class="admin-muted">
          Для публикации добавьте хотя бы один видимый шаг.
        </p>
      </section>
      </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.publish-grid { display: grid; grid-template-columns: minmax(0, 1fr) 460px; align-items: start; gap: 20px; }
.publish-main, .publish-rail { display: grid; gap: 16px; min-width: 0; }
.publish-rail h2 { margin: 0; font-size: 18px; }
.publish-modules { display: grid; gap: 0; margin-top: 12px; }
.publish-modules > div { display: flex; align-items: center; gap: 9px; padding: 11px 0; border-top: 1px solid #e1e6f0; font-size: 13px; }
.publish-modules > div span:last-child { margin-left: auto; color: #4a546b; }
.publish-dot { width: 9px; height: 9px; border-radius: 50%; background: #3457f0; }
@media (max-width: 1000px) { .publish-grid { grid-template-columns: 1fr; } }
.publish-checks {
  display: grid;
  gap: 1px;
  border: 1px solid #e8edf5;
  border-radius: 11px;
  overflow: hidden;
  background: #e8edf5;
}
.publish-checks > div {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: #fff;
}
.publish-checks strong {
  display: block;
  color: #20304b;
  font-size: 13px;
}
.publish-checks small {
  display: block;
  margin-top: 4px;
  color: #8190a6;
  font-size: 11px;
}
.check-good,
.check-warn {
  display: grid;
  width: 28px;
  height: 28px;
  flex: none;
  place-items: center;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 800;
}
.check-good {
  background: #e8f7ef;
  color: #168054;
}
.check-warn {
  background: #fff3e3;
  color: #a05c16;
}
</style>
