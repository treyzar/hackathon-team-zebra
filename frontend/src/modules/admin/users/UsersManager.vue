<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { getApiErrorMessage } from "@/api/errors";
import { userApi } from "./api";
import { groupApi } from "../groups/api";
import type { AdminRole, AdminUser, Group } from "../shared/types";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const users = ref<AdminUser[]>([]);
const groups = ref<Group[]>([]);
const memberships = ref<Record<number, string>>({});
const membershipsComplete = ref(false);
const drafts = ref<Record<number, AdminRole>>({});
const filter = ref<AdminRole>("student");
const selectedIds = ref<number[]>([]);
const selectedUserId = ref<number | null>(null);
const groupTarget = ref<number | "">("");
const assigning = ref(false);
const query = ref("");
const loading = ref(true);
const busyId = ref<number | null>(null);
const error = ref("");
const success = ref("");
const labels: Record<AdminRole, string> = {
  student: "Ученик",
  curator: "Куратор",
  admin: "Администратор",
};
const filtered = computed(() =>
  users.value.filter(
    (user) =>
      user.role === filter.value &&
      `${user.username} ${user.email}`.toLowerCase().includes(query.value.toLowerCase()),
  ),
);
const selectedUser = computed(() => filtered.value.find((user) => user.id === selectedUserId.value) ?? filtered.value[0] ?? null);
const allVisibleSelected = computed(() => filtered.value.length > 0 && filtered.value.every((user) => selectedIds.value.includes(user.id)));
function toggleUser(id: number): void {
  selectedIds.value = selectedIds.value.includes(id) ? selectedIds.value.filter((item) => item !== id) : [...selectedIds.value, id];
  selectedUserId.value = id;
}
function toggleAll(): void {
  selectedIds.value = allVisibleSelected.value ? selectedIds.value.filter((id) => !filtered.value.some((user) => user.id === id)) : [...new Set([...selectedIds.value, ...filtered.value.map((user) => user.id)])];
}
const roleCount = (role: AdminRole): number => users.value.filter((user) => user.role === role).length;

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    users.value = await userApi.users();
    let groupsLoaded = false;
    try {
      groups.value = await groupApi.groups();
      groupsLoaded = true;
    } catch {
      groups.value = [];
    }
    const memberLists = await Promise.allSettled(groups.value.map((group) => groupApi.groupStudents(group.id)));
    membershipsComplete.value = groupsLoaded && memberLists.every((result) => result.status === "fulfilled");
    memberships.value = Object.fromEntries(memberLists.flatMap((result, index) => result.status === "fulfilled" ? result.value.map((user) => [user.id, groups.value[index]!.name]) : []));
    drafts.value = Object.fromEntries(users.value.map((user) => [user.id, user.role]));
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}
async function assignGroup(): Promise<void> {
  if (groupTarget.value === "" || !selectedIds.value.length) return;
  assigning.value = true;
  error.value = "";
  success.value = "";
  try {
    for (const id of selectedIds.value) await groupApi.addStudent(groupTarget.value, id);
    const groupName = groups.value.find((group) => group.id === groupTarget.value)?.name;
    if (groupName) memberships.value = { ...memberships.value, ...Object.fromEntries(selectedIds.value.map((id) => [id, groupName])) };
    success.value = `${selectedIds.value.length} учеников добавлено в группу`;
    selectedIds.value = [];
    groupTarget.value = "";
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    assigning.value = false;
  }
}
async function changeRole(user: AdminUser): Promise<void> {
  const role = drafts.value[user.id];
  if (!role || role === user.role) return;
  busyId.value = user.id;
  error.value = "";
  success.value = "";
  try {
    const updated = await userApi.setRole(user.id, role);
    users.value = users.value.map((item) => (item.id === user.id ? updated : item));
    const nextMemberships = { ...memberships.value };
    delete nextMemberships[user.id];
    memberships.value = nextMemberships;
    selectedIds.value = selectedIds.value.filter((id) => id !== user.id);
    success.value = `Роль пользователя ${user.username} изменена`;
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
    drafts.value[user.id] = user.role;
  } finally {
    busyId.value = null;
  }
}
onMounted(load);
</script>

<template>
  <div class="admin-page">
    <Teleport to="#admin-page-header">
    <div class="admin-toolbar">
      <div>
        <h2>Пользователи</h2>
      </div>
    </div>
    </Teleport>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="success" class="admin-success" role="status">{{ success }}</p>
    <div class="admin-workspace-grid">
    <section class="users-workspace">
      <div class="admin-toolbar">
        <div class="admin-tabs" role="tablist" aria-label="Роль">
          <button
            v-for="item in [
              { key: 'student', label: 'Ученики' },
              { key: 'curator', label: 'Кураторы' },
              { key: 'admin', label: 'Администраторы' },
            ]"
            :key="item.key"
            type="button"
            role="tab"
            :aria-selected="filter === item.key"
            @click="filter = item.key as typeof filter"
          >
            {{ item.label }} · {{ roleCount(item.key as AdminRole) }}
          </button>
        </div>
        <input
          v-model="query"
          class="admin-input"
          style="max-width: 280px"
          aria-label="Поиск пользователя"
          placeholder="Имя или почта"
        />
      </div>
      <div v-if="loading" class="admin-table-wrap admin-empty">Загружаем пользователей…</div>
      <div v-else-if="!filtered.length" class="admin-table-wrap admin-empty">Пользователи не найдены</div>
      <div v-else class="admin-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th><input type="checkbox" :checked="allVisibleSelected" :disabled="filter !== 'student'" aria-label="Выбрать всех" @change="toggleAll" /></th>
              <th>Имя</th>
              <th>Класс</th>
              <th>Группа</th>
              <th>Вход</th>
              <th>Был</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filtered" :key="user.id">
              <td><input type="checkbox" :checked="selectedIds.includes(user.id)" :disabled="user.role !== 'student'" :aria-label="`Выбрать ${user.username}`" @change="toggleUser(user.id)" /></td>
              <td>
                <button class="user-select" type="button" @click="selectedUserId = user.id">{{ user.username }}</button
                ><small
                  >{{ user.email }} <span v-if="user.id === auth.user?.id">· это вы</span></small
                >
              </td>
              <td class="admin-muted">—</td>
              <td :class="{ 'user-no-group': user.role === 'student' && membershipsComplete && !memberships[user.id] }">{{ user.role === 'student' ? memberships[user.id] || (membershipsComplete ? 'не в группе' : '—') : '—' }}</td>
              <td class="admin-muted">—</td>
              <td class="admin-muted">—</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="selectedIds.length" class="users-bulk-bar">
        <strong>Выбрано: {{ selectedIds.length }}</strong>
        <select v-model="groupTarget" class="admin-input" aria-label="Группа для выбранных учеников"><option value="">Выберите группу</option><option v-for="group in groups" :key="group.id" :value="group.id">{{ group.name }}</option></select>
        <button class="admin-button admin-button--primary" type="button" :disabled="groupTarget === '' || assigning" @click="assignGroup">{{ assigning ? 'Назначаем…' : 'В группу…' }}</button>
      </div>
    </section>
    <aside class="users-profile" aria-label="Карточка пользователя">
      <h3>Карточка пользователя</h3>
      <div class="admin-rail-card users-profile-card" v-if="selectedUser">
        <strong>{{ selectedUser.username }}</strong>
        <div class="users-avatar" aria-hidden="true">{{ selectedUser.username.slice(0, 2).toUpperCase() }}</div>
        <span>{{ selectedUser.email }}</span>
        <span class="admin-badge">{{ labels[selectedUser.role] }}</span>
        <div class="profile-role-editor">
          <label class="admin-field">Роль
            <select v-model="drafts[selectedUser.id]" :disabled="selectedUser.id === auth.user?.id || busyId === selectedUser.id">
              <option value="student">Ученик</option><option value="curator">Куратор</option><option value="admin">Администратор</option>
            </select>
          </label>
          <button class="admin-button admin-button--primary" type="button" :disabled="selectedUser.id === auth.user?.id || drafts[selectedUser.id] === selectedUser.role || busyId === selectedUser.id" @click="changeRole(selectedUser)">{{ busyId === selectedUser.id ? 'Сохраняем…' : 'Сохранить роль' }}</button>
        </div>
      </div>
      <p>В текущем API нет QR-карточек входа и данных о последнем посещении.</p>
    </aside>
    </div>
    <p class="admin-muted">
      При смене роли пользователь может быть исключён из группы, если новая роль не подходит. Свою
      роль изменить нельзя.
    </p>
  </div>
</template>

<style scoped>
.users-workspace { display: grid; gap: 16px; }
.admin-table { min-width: 680px; }
.admin-table th:first-child, .admin-table td:first-child { width: 38px; }
.user-no-group { color: #b8520f !important; }
.user-select { padding: 0; border: 0; background: none; color: #0f172a; font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; }
.user-select:hover { color: #3457f0; }
.users-bulk-bar { display: flex; align-items: center; gap: 8px; min-height: 60px; padding: 10px 14px; border-radius: 12px; background: #0f172a; color: #fff; }
.users-bulk-bar strong { flex: 1; }
.users-bulk-bar select { max-width: 180px; }
.users-profile { display: grid; align-content: start; gap: 10px; }
.users-profile h3 { margin: 0; font-size: 16px; }
.users-profile > p { margin: 0; color: #4a546b; font-size: 13px; line-height: 1.5; }
.users-profile-card { display: grid; justify-items: center; gap: 12px; padding: 20px; text-align: center; }
.users-profile-card > strong { font-size: 20px; }
.users-profile-card > span:not(.admin-badge) { color: #4a546b; font-size: 13px; }
.users-avatar { display: grid; width: 150px; height: 150px; place-items: center; border: 2px solid #0f172a; border-radius: 12px; background: #eaf0fe; color: #3457f0; font-size: 40px; font-weight: 700; }
.profile-role-editor { display: grid; justify-items: stretch; gap: 8px; width: 100%; margin-top: 8px; text-align: left; }
</style>
