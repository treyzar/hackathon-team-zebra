<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { getApiErrorMessage } from "@/api/errors";
import { groupApi } from "./api";
import { userApi } from "../users/api";
import type { AdminUser, Group } from "../shared/types";

const groups = ref<Group[]>([]);
const users = ref<AdminUser[]>([]);
const members = ref<AdminUser[]>([]);
const selectedId = ref<number | null>(null);
const newName = ref("");
const newCurator = ref<number | "">("");
const editName = ref("");
const editCurator = ref<number | "">("");
const studentToAdd = ref<number | "">("");
const showCreate = ref(false);
const loading = ref(true);
const busy = ref(false);
const error = ref("");
const success = ref("");
const selected = computed(
  () => groups.value.find((group) => group.id === selectedId.value) ?? null,
);
const curators = computed(() => users.value.filter((user) => user.role === "curator"));
const students = computed(() => users.value.filter((user) => user.role === "student"));
const available = computed(() =>
  students.value.filter((user) => !members.value.some((member) => member.id === user.id)),
);
function username(id: number | null): string {
  return users.value.find((user) => user.id === id)?.username ?? "Не назначен";
}

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    [groups.value, users.value] = await Promise.all([groupApi.groups(), userApi.users()]);
    if (selectedId.value === null && groups.value.length) selectedId.value = groups.value[0]!.id;
    if (selectedId.value !== null && !groups.value.some((group) => group.id === selectedId.value))
      selectedId.value = groups.value[0]?.id ?? null;
    await loadMembers();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}
async function loadMembers(): Promise<void> {
  if (selectedId.value === null) {
    members.value = [];
    return;
  }
  members.value = await groupApi.groupStudents(selectedId.value);
}
async function create(): Promise<void> {
  if (!newName.value.trim()) return;
  busy.value = true;
  error.value = "";
  success.value = "";
  try {
    const group = await groupApi.createGroup({
      name: newName.value.trim(),
      curator_id: newCurator.value === "" ? null : newCurator.value,
    });
    selectedId.value = group.id;
    showCreate.value = false;
    newName.value = "";
    newCurator.value = "";
    await load();
    success.value = "Группа создана";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}
async function save(): Promise<void> {
  if (!selected.value || !editName.value.trim()) return;
  busy.value = true;
  error.value = "";
  success.value = "";
  try {
    await groupApi.updateGroup(selected.value.id, {
      name: editName.value.trim(),
      curator_id: editCurator.value === "" ? null : editCurator.value,
    });
    await load();
    success.value = "Группа обновлена";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}
async function addStudent(): Promise<void> {
  if (selectedId.value === null || studentToAdd.value === "") return;
  busy.value = true;
  error.value = "";
  success.value = "";
  try {
    await groupApi.addStudent(selectedId.value, studentToAdd.value);
    studentToAdd.value = "";
    await load();
    success.value = "Ученик добавлен в группу";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}
async function removeStudent(userId: number): Promise<void> {
  if (selectedId.value === null) return;
  busy.value = true;
  error.value = "";
  success.value = "";
  try {
    await groupApi.removeStudent(selectedId.value, userId);
    await load();
    success.value = "Ученик исключён из группы";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}
async function deleteGroup(): Promise<void> {
  if (!selected.value || !window.confirm(`Удалить группу «${selected.value.name}»?`)) return;
  busy.value = true;
  error.value = "";
  success.value = "";
  try {
    await groupApi.deleteGroup(selected.value.id);
    selectedId.value = null;
    await load();
    success.value = "Группа удалена";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    busy.value = false;
  }
}
watch(selected, (group) => {
  editName.value = group?.name ?? "";
  editCurator.value = group?.curator_id ?? "";
});
watch(selectedId, () => {
  if (!loading.value) loadMembers().catch((cause) => (error.value = getApiErrorMessage(cause)));
});
onMounted(load);
</script>

<template>
  <div class="admin-page">
    <Teleport to="#admin-page-header">
    <div class="admin-toolbar">
      <div>
        <h2>Группы</h2>
      </div>
      <button
        class="admin-button admin-button--primary"
        type="button"
        @click="showCreate = !showCreate"
      >
        + Группа
      </button>
    </div>
    </Teleport>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="success" class="admin-success" role="status">{{ success }}</p>
    <section v-if="showCreate" class="admin-panel">
      <div class="admin-panel-head">
        <div>
          <h2>Новая группа</h2>
          <p>Куратора можно назначить позже.</p>
        </div>
      </div>
      <form class="admin-form" @submit.prevent="create">
        <div class="admin-form-row">
          <label class="admin-field"
            >Название<input
              v-model="newName"
              maxlength="200"
              required
              placeholder="Например, 5А" /></label
          ><label class="admin-field"
            >Куратор<select v-model="newCurator">
              <option value="">Не назначен</option>
              <option v-for="user in curators" :key="user.id" :value="user.id">
                {{ user.username }}
              </option>
            </select></label
          >
        </div>
        <div class="admin-actions">
          <button class="admin-button admin-button--primary" :disabled="busy">Создать</button
          ><button class="admin-button" type="button" @click="showCreate = false">Отмена</button>
        </div>
      </form>
    </section>
    <div v-if="loading" class="admin-panel admin-empty">Загружаем группы…</div>
    <div v-else class="groups-layout">
      <section class="admin-panel">
        <div v-if="!groups.length" class="admin-empty">Групп пока нет</div>
        <div v-else class="admin-list">
          <button
            v-for="group in groups"
            :key="group.id"
            class="group-card"
            :class="{ 'group-card--active': selectedId === group.id }"
            type="button"
            @click="selectedId = group.id"
          >
            <span
              ><strong>{{ group.name }}</strong
              ><small>{{ username(group.curator_id) }} · {{ group.students_count }} учеников</small></span
            ><span class="group-chevron" aria-hidden="true">›</span>
          </button>
        </div>
      </section>
      <div v-if="selected" class="admin-stack">
        <section class="admin-panel">
          <div class="admin-panel-head">
            <div>
              <h2>{{ selected.name }}</h2>
              <p>{{ username(selected.curator_id) }} · {{ selected.students_count }} учеников</p>
            </div>
          </div>
          <form class="admin-form" @submit.prevent="save">
            <label class="admin-field"
              >Название<input v-model="editName" maxlength="200" required /></label
            ><label class="admin-field"
              >Куратор<select v-model="editCurator">
                <option value="">Не назначен</option>
                <option v-for="user in curators" :key="user.id" :value="user.id">
                  {{ user.username }}
                </option>
              </select></label
            ><button class="admin-button admin-button--primary" :disabled="busy">Сохранить</button>
          </form>
          <p class="group-help">Куратор видит очередь работ и вопросы только своих групп.</p>
          <div class="group-courses">
            <strong>Курсы группы</strong>
            <span>Нет данных о назначенных курсах</span>
            <button class="admin-button group-course-add" type="button" disabled title="Назначение курсов группам отсутствует в текущем API">+ Назначить курс</button>
          </div>
          <hr class="admin-divider" style="margin: 22px 0" />
          <button
            class="admin-button admin-button--danger"
            type="button"
            :disabled="busy"
            @click="deleteGroup"
          >
            Удалить группу
          </button>
        </section>
        <section class="admin-panel">
          <div class="admin-panel-head">
            <div>
              <h2>Ученики</h2>
              <p>{{ members.length }} в группе</p>
            </div>
          </div>
          <div v-if="!members.length" class="admin-empty">Учеников пока нет</div>
          <div v-else class="admin-table-wrap">
            <table class="admin-table">
              <thead><tr><th>Ученик</th><th>Класс</th><th>Прогресс</th><th>Отставание</th><th>Последний вход</th><th></th></tr></thead>
              <tbody>
                <tr v-for="member in members" :key="member.id">
                  <td><strong>{{ member.username }}</strong><small>{{ member.email }}</small></td>
                  <td>—</td>
                  <td><span class="group-progress-placeholder" aria-label="Данные о прогрессе недоступны" /></td>
                  <td>—</td>
                  <td>—</td>
                  <td><button class="admin-button admin-button--danger" type="button" :disabled="busy" @click="removeStudent(member.id)">Исключить</button></td>
                </tr>
              </tbody>
            </table>
          </div>
          <form class="admin-form" style="margin-top: 20px" @submit.prevent="addStudent">
            <label class="admin-field"
              >Добавить ученика<select v-model="studentToAdd" required>
                <option value="" disabled>Выберите пользователя</option>
                <option v-for="student in available" :key="student.id" :value="student.id">
                  {{ student.username }} · {{ student.email }}
                </option>
              </select></label
            ><button
              class="admin-button admin-button--subtle"
              :disabled="busy || studentToAdd === ''"
            >
              Добавить в группу
            </button>
            <p class="admin-muted">
              Если ученик уже состоит в другой группе, он будет перенесён сюда.
            </p>
          </form>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.groups-layout { display: grid; grid-template-columns: 300px minmax(0, 1fr); align-items: start; gap: 20px; }
.groups-layout > .admin-panel { padding: 0; border: 0; background: transparent; }
.groups-layout > .admin-stack { min-width: 0; }
.groups-layout .admin-table { min-width: 760px; }
.group-progress-placeholder { display: inline-block; width: 110px; height: 6px; border-radius: 999px; background: #e1e6f0; }
.groups-layout .admin-stack > .admin-panel:first-child form { display: flex; flex-wrap: wrap; align-items: end; gap: 12px; }
.groups-layout .admin-stack > .admin-panel:first-child form .admin-field:first-child { flex: 1 1 180px; }
.groups-layout .admin-stack > .admin-panel:first-child form .admin-field:nth-child(2) { flex: 1 1 200px; }
.group-help { margin: 12px 0 0; color: #4a546b; font-size: 12px; }
.group-courses { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 16px; padding-top: 14px; border-top: 1px solid #e1e6f0; font-size: 13px; }
.group-courses span { padding: 4px 10px; border-radius: 999px; background: #eaf0fe; color: #4a546b; }
.group-course-add { min-height: 32px; border: 1px dashed #3457f0; border-radius: 999px; color: #3457f0; }
.group-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  width: 100%;
  padding: 14px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: #fff;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.group-card--active {
  border-color: #3457f0;
  background: #eef2ff;
}
.group-card strong {
  display: block;
  color: #1d2b43;
  font-size: 13px;
}
.group-card small {
  display: block;
  margin-top: 5px;
  color: #8995a7;
  font-size: 11px;
}
.group-chevron { color: #9ba5b8; font-size: 24px; }
@media (max-width: 850px) { .groups-layout { grid-template-columns: 1fr; } }
</style>
