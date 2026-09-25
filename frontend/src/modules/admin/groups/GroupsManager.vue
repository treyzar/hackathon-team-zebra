<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { getApiErrorMessage } from "@/api/errors";
import { groupApi } from "./api";
import { courseEnrollmentApi } from "./courseEnrollmentApi";
import { userApi } from "../users/api";
import GroupList from "./components/GroupList.vue";
import GroupCreatePanel from "./components/GroupCreatePanel.vue";
import GroupSettingsPanel from "./components/GroupSettingsPanel.vue";
import GroupStudentsPanel from "./components/GroupStudentsPanel.vue";
import GroupCoursesPanel from "./components/GroupCoursesPanel.vue";
import { useNotifications } from "@/modules/notifications/useNotifications";
import type { AdminUser, Group } from "../shared/types";
import type { AdminCourse, GroupCourseCoverage } from "./types";

const groups = ref<Group[]>([]);
const users = ref<AdminUser[]>([]);
const members = ref<AdminUser[]>([]);
const courses = ref<AdminCourse[]>([]);
const courseCoverage = ref<GroupCourseCoverage[]>([]);

const selectedId = ref<number | null>(null);
const showCreate = ref(false);
const loading = ref(true);
const coursesLoading = ref(false);
const busy = ref(false);
const notifications = useNotifications();

const selected = computed(
  () => groups.value.find((group) => group.id === selectedId.value) ?? null,
);
const curators = computed(() => users.value.filter((user) => user.role === "curator"));
const students = computed(() => users.value.filter((user) => user.role === "student"));

function username(id: number | null): string {
  return users.value.find((user) => user.id === id)?.username ?? "Нет куратора";
}

async function loadBase(): Promise<void> {
  loading.value = true;
  try {
    [groups.value, users.value, courses.value] = await Promise.all([
      groupApi.groups(),
      userApi.users(),
      courseEnrollmentApi.courses(),
    ]);

    if (selectedId.value === null && groups.value.length) {
      selectedId.value = groups.value[0]!.id;
    } else if (
      selectedId.value !== null &&
      !groups.value.some((group) => group.id === selectedId.value)
    ) {
      selectedId.value = groups.value[0]?.id ?? null;
    }

    await loadSelectedGroupData();
  } catch (cause) {
    notifications.error(getApiErrorMessage(cause));
  } finally {
    loading.value = false;
  }
}

async function loadSelectedGroupData(): Promise<void> {
  // Course coverage depends on the current member list, so keep this sequential.
  await loadMembers();
  await loadCourseCoverage();
}

async function loadMembers(): Promise<void> {
  if (selectedId.value === null) {
    members.value = [];
    return;
  }
  members.value = await groupApi.groupStudents(selectedId.value);
}

async function loadCourseCoverage(): Promise<void> {
  if (selectedId.value === null) {
    courseCoverage.value = [];
    return;
  }

  coursesLoading.value = true;
  try {
    const groupId = selectedId.value;
    const memberIds = new Set(members.value.map((member) => member.id));

    // OpenAPI exposes enrollments only per course, not per group. To display group coverage
    // we have to inspect each course enrollment list and intersect it with current group members.
    const enrollmentLists = await Promise.all(
      courses.value.map((course) => courseEnrollmentApi.enrollments(course.id)),
    );

    courseCoverage.value = courses.value.map((course, index) => {
      const enrolledStudentIds = enrollmentLists[index]!.filter(
        (student) => student.group_id === groupId && memberIds.has(student.id),
      ).map((student) => student.id);

      return {
        course,
        enrolledStudentIds,
        enrolledCount: enrolledStudentIds.length,
        studentsCount: members.value.length,
      };
    });
  } finally {
    coursesLoading.value = false;
  }
}

async function createGroup(payload: { name: string; curator_id: number | null }): Promise<void> {
  busy.value = true;
  try {
    const group = await groupApi.createGroup(payload);
    selectedId.value = group.id;
    showCreate.value = false;
    await loadBase();
    notifications.success("Группа создана");
  } catch (cause) {
    notifications.error(getApiErrorMessage(cause));
  } finally {
    busy.value = false;
  }
}

async function saveGroup(payload: { name: string; curator_id: number | null }): Promise<void> {
  if (!selected.value) return;
  busy.value = true;
  try {
    await groupApi.updateGroup(selected.value.id, payload);
    groups.value = await groupApi.groups();
    notifications.success("Группа обновлена");
  } catch (cause) {
    notifications.error(getApiErrorMessage(cause));
  } finally {
    busy.value = false;
  }
}

async function addStudent(userId: number): Promise<void> {
  if (selectedId.value === null) return;
  busy.value = true;
  try {
    await groupApi.addStudent(selectedId.value, userId);
    [groups.value, members.value] = await Promise.all([
      groupApi.groups(),
      groupApi.groupStudents(selectedId.value),
    ]);
    await loadCourseCoverage();
    notifications.success("Ученик добавлен в группу");
  } catch (cause) {
    notifications.error(getApiErrorMessage(cause));
  } finally {
    busy.value = false;
  }
}

async function removeStudent(userId: number): Promise<void> {
  if (selectedId.value === null) return;
  busy.value = true;
  try {
    await groupApi.removeStudent(selectedId.value, userId);
    [groups.value, members.value] = await Promise.all([
      groupApi.groups(),
      groupApi.groupStudents(selectedId.value),
    ]);
    await loadCourseCoverage();
    notifications.success("Ученик исключён из группы");
  } catch (cause) {
    notifications.error(getApiErrorMessage(cause));
  } finally {
    busy.value = false;
  }
}

async function enrollGroup(courseId: number): Promise<void> {
  if (selectedId.value === null) return;
  busy.value = true;
  try {
    const result = await courseEnrollmentApi.enrollGroup(courseId, selectedId.value);
    await loadCourseCoverage();

    const enrolled = result.enrolled.length;
    const existed = result.already_enrolled.length;
    notifications.success(
      enrolled
        ? `На курс записано: ${enrolled}. Уже были записаны: ${existed}.`
        : `Все текущие ученики группы уже были записаны на этот курс (${existed}).`,
    );
  } catch (cause) {
    notifications.error(getApiErrorMessage(cause));
  } finally {
    busy.value = false;
  }
}

async function deleteGroup(): Promise<void> {
  if (!selected.value || !window.confirm(`Удалить группу «${selected.value.name}»?`)) return;
  busy.value = true;
  try {
    await groupApi.deleteGroup(selected.value.id);
    selectedId.value = null;
    await loadBase();
    notifications.success("Группа удалена");
  } catch (cause) {
    notifications.error(getApiErrorMessage(cause));
  } finally {
    busy.value = false;
  }
}

watch(selectedId, async () => {
  if (loading.value) return;
  try {
    await loadSelectedGroupData();
  } catch (cause) {
    notifications.error(getApiErrorMessage(cause));
  }
});

onMounted(loadBase);
</script>

<template>
  <div class="groups-page">
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

    <GroupCreatePanel
      v-if="showCreate"
      class="groups-create-panel"
      :curators="curators"
      :busy="busy"
      @create="createGroup"
      @cancel="showCreate = false"
    />

    <div v-if="loading" class="groups-loading">Загружаем группы…</div>
    <div v-else class="groups-layout">
      <GroupList
        :groups="groups"
        :selected-id="selectedId"
        :curator-name="username"
        @select="selectedId = $event"
      />

      <main v-if="selected" class="group-content">
        <section class="group-summary-card">
          <GroupSettingsPanel
            :group="selected"
            :curators="curators"
            :busy="busy"
            @save="saveGroup"
            @delete="deleteGroup"
          />

          <GroupCoursesPanel
            :courses="courseCoverage"
            :loading="coursesLoading"
            :busy="busy"
            @enroll="enrollGroup"
          />
        </section>

        <GroupStudentsPanel
          :members="members"
          :students="students"
          :busy="busy"
          @add="addStudent"
          @remove="removeStudent"
        />
      </main>

      <main v-else class="group-content group-content--empty">
        Создайте первую группу, чтобы начать работу.
      </main>
    </div>
  </div>
</template>

<style scoped>
.groups-page {
  min-width: 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 24px 32px;
  background: #f4f6fb;
  color: #1d2b43;
  font-size: 14px;
  line-height: 1.5;
}
.groups-page-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.groups-page-header h2 {
  margin: 0;
}
.groups-layout {
  min-height: 0;
  flex: 1;
  display: flex;
  align-items: stretch;
  gap: 20px;
  overflow: hidden;
}
.group-content {
  min-width: 0;
  min-height: 0;
  height: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 4px;
  scrollbar-gutter: stable;
}
.group-summary-card {
  flex: 0 0 auto;
  padding: 18px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.group-content--empty,
.groups-loading {
  min-height: 180px;
  align-items: center;
  justify-content: center;
  border: 1px dashed #cbd3e2;
  border-radius: 16px;
  color: #6e788d;
  background: rgba(255, 255, 255, 0.55);
}
.groups-loading {
  display: flex;
  flex: 1;
}
.groups-create-panel {
  flex: 0 0 auto;
  margin-bottom: 16px;
}
@media (max-width: 900px) {
  .groups-page {
    height: auto;
    min-height: 100%;
    overflow: visible;
    padding: 20px;
  }
  .groups-layout {
    overflow: visible;
    flex-direction: column;
  }
  .group-content {
    width: 100%;
    height: auto;
    overflow: visible;
    padding-right: 0;
  }
}
@media (max-width: 560px) {
  .groups-page {
    padding: 14px;
  }
}
</style>
