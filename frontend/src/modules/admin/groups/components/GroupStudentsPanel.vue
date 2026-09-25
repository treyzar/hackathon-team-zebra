<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { AdminUser } from "../../shared/types";

const props = defineProps<{
  members: AdminUser[];
  students: AdminUser[];
  busy: boolean;
}>();

const emit = defineEmits<{
  add: [userId: number];
  remove: [userId: number];
}>();

const query = ref("");
const adding = ref(false);
const studentToAdd = ref<number | "">("");

const filteredMembers = computed(() => {
  const q = query.value.trim().toLocaleLowerCase();
  if (!q) return props.members;
  return props.members.filter((member) =>
    `${member.username} ${member.email}`.toLocaleLowerCase().includes(q),
  );
});

const available = computed(() => {
  const memberIds = new Set(props.members.map((member) => member.id));
  return props.students.filter((student) => !memberIds.has(student.id));
});

watch(
  () => props.members,
  () => {
    if (
      studentToAdd.value !== "" &&
      !available.value.some((student) => student.id === studentToAdd.value)
    ) {
      studentToAdd.value = "";
    }
  },
);

function add(): void {
  if (studentToAdd.value === "" || props.busy) return;
  emit("add", studentToAdd.value);
  studentToAdd.value = "";
  adding.value = false;
}
</script>

<template>
  <section class="students-card">
    <div class="students-head">
      <strong>Ученики · {{ members.length }}</strong>
      <input v-model="query" aria-label="Поиск ученика" placeholder="Поиск по имени или email" />
      <button type="button" :disabled="busy || !available.length" @click="adding = !adding">
        Добавить учеников
      </button>
    </div>

    <form v-if="adding" class="student-add" @submit.prevent="add">
      <select v-model="studentToAdd" required>
        <option value="" disabled>Выберите ученика</option>
        <option v-for="student in available" :key="student.id" :value="student.id">
          {{ student.username }} · {{ student.email }}
        </option>
      </select>
      <button :disabled="busy || studentToAdd === ''">Добавить в группу</button>
      <span>Если ученик уже в другой группе, API перенесёт его сюда.</span>
    </form>

    <div v-if="!members.length" class="students-empty">Учеников пока нет</div>
    <div v-else-if="!filteredMembers.length" class="students-empty">Ничего не найдено</div>
    <div v-else class="students-table">
      <div class="students-row students-row--head">
        <span>УЧЕНИК</span>
        <span>EMAIL</span>
        <span></span>
      </div>
      <div v-for="member in filteredMembers" :key="member.id" class="students-row">
        <strong>{{ member.username }}</strong>
        <span class="students-email">{{ member.email }}</span>
        <div class="students-actions">
          <button type="button" :disabled="busy" @click="emit('remove', member.id)">
            Исключить
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.students-card {
  overflow: hidden;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.students-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
}
.students-head strong {
  flex: 1;
  color: #1d2b43;
  font-size: 16px;
}
.students-head input {
  width: 220px;
  height: 40px;
  box-sizing: border-box;
  padding: 0 12px;
  border: 1px solid #d9dfeb;
  border-radius: 10px;
  outline: none;
  font: inherit;
}
.students-head input:focus {
  border-color: #3457f0;
  box-shadow: 0 0 0 3px rgba(52, 87, 240, 0.1);
}
.students-head button,
.student-add button {
  height: 40px;
  padding: 0 14px;
  border: 1px solid #e1e6f0;
  border-radius: 12px;
  background: #fff;
  color: #1d2b43;
  font:
    600 14px Onest,
    system-ui,
    sans-serif;
  cursor: pointer;
}
.student-add {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 0 16px 12px;
}
.student-add select {
  min-width: 280px;
  height: 38px;
  padding: 0 11px;
  border: 1px solid #d9dfeb;
  border-radius: 10px;
  background: #fff;
  font: inherit;
}
.student-add button {
  height: 38px;
  border-color: #3457f0;
  background: #3457f0;
  color: #fff;
}
.student-add span {
  color: #6c768a;
  font-size: 12px;
}
.students-table {
  min-width: 620px;
}
.students-row {
  display: grid;
  grid-template-columns: minmax(180px, 1.1fr) minmax(260px, 2fr) 110px;
  align-items: center;
  gap: 16px;
  min-height: 54px;
  padding: 0 16px;
  border-top: 1px solid #edf0f6;
  color: #1d2b43;
}
.students-row--head {
  min-height: 36px;
  border-top: 0;
  background: #f4f6fb;
  color: #4a546b;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.students-email {
  overflow: hidden;
  color: #4a546b;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.students-actions {
  text-align: right;
}
.students-actions button {
  border: 0;
  background: transparent;
  color: #9a3c3c;
  font:
    600 13px Onest,
    system-ui,
    sans-serif;
  cursor: pointer;
}
.students-actions button:disabled,
.students-head button:disabled,
.student-add button:disabled {
  opacity: 0.5;
  cursor: default;
}
.students-empty {
  padding: 32px 16px;
  border-top: 1px solid #edf0f6;
  color: #6c768a;
  text-align: center;
}
@media (max-width: 760px) {
  .students-head {
    flex-wrap: wrap;
  }
  .students-head strong {
    flex-basis: 100%;
  }
  .students-head input {
    width: auto;
    flex: 1 1 180px;
  }
  .students-card {
    overflow-x: auto;
  }
}
</style>
