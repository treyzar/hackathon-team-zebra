<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { courseApi } from "./api";
import { groupApi } from "../groups/api";
import { docToText, textToDoc } from "../shared/format";
import type { Course, CourseTree, Group, StepAccess } from "../shared/types";
import { ADMIN_COURSE_ROUTE } from "@/pages/admin/course/constants";
import { ADMIN_GROUPS_ROUTE } from "@/pages/admin/groups/constants";
import { ADMIN_IMPORT_ROUTE } from "@/pages/admin/import/constants";

const router = useRouter();
const courses = ref<Course[]>([]);
const groups = ref<Group[]>([]);
const groupsLoaded = ref(false);
const structures = ref<Record<number, { modules: number; steps: number }>>({});
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const filter = ref<"all" | "published" | "draft">("all");
const showCreate = ref(false);
const title = ref("");
const slug = ref("");
const description = ref("");
const stepAccess = ref<StepAccess>("all");

const filtered = computed(() =>
  courses.value.filter((course) => {
    const statusMatches =
      filter.value === "all" ||
      (filter.value === "published" ? course.is_published : !course.is_published);
    return statusMatches;
  }),
);
const publishedCount = computed(() => courses.value.filter((course) => course.is_published).length);
const totalModules = computed(() =>
  Object.values(structures.value).reduce((sum, item) => sum + item.modules, 0),
);
const totalSteps = computed(() =>
  Object.values(structures.value).reduce((sum, item) => sum + item.steps, 0),
);

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    courses.value = await courseApi.courses();
    try {
      groups.value = await groupApi.groups();
      groupsLoaded.value = true;
    } catch {
      groupsLoaded.value = false;
    }
    const trees = await Promise.allSettled(
      courses.value.map((course) => courseApi.course(course.id)),
    );
    structures.value = Object.fromEntries(
      trees.flatMap((result) => {
        if (result.status !== "fulfilled") return [];
        const tree: CourseTree = result.value;
        return [
          [
            tree.id,
            {
              modules: tree.modules.length,
              steps: tree.modules.reduce((sum, module) => sum + module.steps.length, 0),
            },
          ],
        ];
      }),
    );
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}

async function create(): Promise<void> {
  if (!title.value.trim() || !slug.value.trim()) return;
  saving.value = true;
  error.value = "";
  try {
    const course = await courseApi.createCourse({
      title: title.value.trim(),
      slug: slug.value.trim(),
      description: textToDoc(description.value),
      step_access: stepAccess.value,
    });
    await router.push({ name: ADMIN_COURSE_ROUTE.name, params: { courseId: course.id } });
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="admin-page">
    <Teleport defer to="#admin-page-header">
      <div class="admin-toolbar">
        <div>
          <h2>Курсы</h2>
        </div>
        <div class="admin-actions">
          <RouterLink class="admin-button" :to="ADMIN_IMPORT_ROUTE.path"
            >Импорт / экспорт</RouterLink
          >
          <button
            class="admin-button admin-button--primary"
            type="button"
            @click="showCreate = !showCreate"
          >
            + Новый курс
          </button>
        </div>
      </div>
    </Teleport>

    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>

    <section v-if="showCreate" class="admin-panel" aria-label="Создание курса">
      <div class="admin-panel-head">
        <div>
          <h2>Новый курс</h2>
          <p>Сначала задайте основу курса. Модули и шаги добавляются в конструкторе.</p>
        </div>
      </div>
      <form class="admin-form" @submit.prevent="create">
        <div class="admin-form-row">
          <label class="admin-field"
            >Название<input
              v-model="title"
              maxlength="200"
              required
              placeholder="Например, Основы Python"
          /></label>
          <label class="admin-field"
            >Адрес курса<input
              v-model="slug"
              maxlength="100"
              pattern="[a-z0-9]+(-[a-z0-9]+)*"
              required
              placeholder="python-basics"
            /><small>Латинские буквы, цифры и дефисы</small></label
          >
        </div>
        <label class="admin-field"
          >Описание<textarea
            v-model="description"
            placeholder="О чём этот курс и чему научится ученик"
          />
        </label>
        <label class="admin-field"
          >Доступ к шагам<select v-model="stepAccess">
            <option value="all">Все шаги сразу</option>
            <option value="sequential">По очереди</option>
          </select></label
        >
        <div class="admin-actions">
          <button class="admin-button admin-button--primary" :disabled="saving">
            {{ saving ? "Создаём…" : "Создать курс" }}</button
          ><button class="admin-button" type="button" @click="showCreate = false">Отмена</button>
        </div>
      </form>
    </section>

    <div class="admin-workspace-grid">
      <div class="admin-workspace-main">
        <div class="admin-toolbar">
          <div class="admin-tabs" role="tablist" aria-label="Статус курса">
            <button
              v-for="tab in [
                { key: 'all', label: 'Все' },
                { key: 'published', label: 'Опубликованные' },
                { key: 'draft', label: 'Черновики' },
              ]"
              :key="tab.key"
              type="button"
              role="tab"
              :aria-selected="filter === tab.key"
              @click="filter = tab.key as typeof filter"
            >
              {{ tab.label }} ·
              {{
                tab.key === "all"
                  ? courses.length
                  : tab.key === "published"
                    ? publishedCount
                    : courses.length - publishedCount
              }}
            </button>
          </div>
        </div>
        <div v-if="loading" class="admin-table-wrap admin-empty">Загружаем курсы…</div>
        <div v-else-if="!filtered.length" class="admin-table-wrap admin-empty">
          Курсов в этом разделе нет
        </div>
        <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead>
              <tr>
                <th>Курс</th>
                <th>Состав</th>
                <th>Статус</th>
                <th>Ученики</th>
                <th>Обновлён</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="course in filtered" :key="course.id">
                <td>
                  <RouterLink
                    class="course-title"
                    :to="{ name: ADMIN_COURSE_ROUTE.name, params: { courseId: course.id } }"
                    >{{ course.title }}</RouterLink
                  >
                  <small>{{ docToText(course.description).trim() || course.slug }}</small>
                </td>
                <td>
                  <span v-if="structures[course.id]"
                    >{{ structures[course.id]?.modules }} мод. ·
                    {{ structures[course.id]?.steps }} шаг.</span
                  >
                  <span v-else class="admin-muted">—</span>
                </td>
                <td>
                  <span
                    class="admin-badge"
                    :class="course.is_published ? 'admin-badge--green' : 'admin-badge--gray'"
                    >{{ course.is_published ? "✓ Опубликован" : "○ Черновик" }}</span
                  >
                </td>
                <td class="admin-muted">—</td>
                <td class="admin-muted">—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <aside class="admin-workspace-aside" aria-label="Сводка по курсам">
        <section class="admin-rail-card">
          <h3>Сигналы по содержанию</h3>
          <div class="course-signal">
            <strong>Курсы и шаги</strong
            ><span
              >{{ courses.length }} курсов · {{ totalModules }} модулей ·
              {{ totalSteps }} шагов</span
            >
          </div>
          <p style="margin-top: 10px">
            Аналитика по ответам появится после подключения данных о попытках.
          </p>
        </section>
        <section class="admin-rail-card">
          <h3>Без назначения</h3>
          <p>
            {{
              groupsLoaded
                ? `${groups.filter((group) => group.curator_id === null).length} групп без куратора`
                : "Данные о группах недоступны"
            }}
          </p>
          <RouterLink class="admin-link" :to="ADMIN_GROUPS_ROUTE.path">Назначить →</RouterLink>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.course-title {
  display: block;
  color: #0f172a !important;
  font-weight: 700;
  text-decoration: none;
}
.course-title:hover {
  color: #3457f0 !important;
}
.admin-table {
  min-width: 660px;
}
.course-signal {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff1e6;
  color: #0f172a;
  font-size: 13px;
}
.course-signal span {
  color: #4a546b;
}
.admin-rail-card .admin-link {
  display: inline-block;
  margin-top: 10px;
}
</style>
