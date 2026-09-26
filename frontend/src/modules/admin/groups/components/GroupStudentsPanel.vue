<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { fullName } from "../../shared/format";
import type { AdminUser } from "../../shared/types";
import { orderByRating, ratingParts } from "../rating";
import type { GroupRatingRow } from "../types";

const props = defineProps<{
  members: AdminUser[];
  students: AdminUser[];
  // null: the rating could not be loaded.
  rating: GroupRatingRow[] | null;
  busy: boolean;
}>();

const emit = defineEmits<{
  add: [userId: number];
  remove: [userId: number];
}>();

const query = ref("");
const adding = ref(false);
const studentToAdd = ref<number | "">("");

const ratingById = computed(
  () => new Map((props.rating ?? []).map((row) => [row.student_id, row])),
);

const filteredMembers = computed(() => {
  const q = query.value.trim().toLocaleLowerCase();
  const ordered = orderByRating(props.members, props.rating);
  if (!q) return ordered;
  return ordered.filter((member) =>
    `${fullName(member)} ${member.username} ${member.email}`.toLocaleLowerCase().includes(q),
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
      <input
        v-model="query"
        aria-label="Поиск ученика"
        placeholder="Поиск по ФИО, логину или email"
      />
      <button type="button" :disabled="busy || !available.length" @click="adding = !adding">
        Добавить учеников
      </button>
    </div>

    <form v-if="adding" class="student-add" @submit.prevent="add">
      <select v-model="studentToAdd" required>
        <option value="" disabled>Выберите ученика</option>
        <option v-for="student in available" :key="student.id" :value="student.id">
          {{ fullName(student) }} · {{ student.email }}
        </option>
      </select>
      <button :disabled="busy || studentToAdd === ''">Добавить в группу</button>
      <span>Если ученик уже в другой группе, API перенесёт его сюда.</span>
    </form>

    <p v-if="rating === null && members.length" class="students-rating-error">
      Не удалось загрузить рейтинг группы.
    </p>

    <div v-if="!members.length" class="students-empty">Учеников пока нет</div>
    <div v-else-if="!filteredMembers.length" class="students-empty">Ничего не найдено</div>
    <div v-else class="students-table" aria-label="Список учеников группы" tabindex="0">
      <div class="students-row students-row--head">
        <span title="Место в рейтинге группы">МЕСТО</span>
        <span>УЧЕНИК</span>
        <span>EMAIL</span>
        <span title="Баллы по всем курсам ученика + 2 балла за каждый день серии">РЕЙТИНГ</span>
        <span></span>
      </div>
      <div v-for="member in filteredMembers" :key="member.id" class="students-row">
        <span class="students-place">{{ ratingById.get(member.id)?.place ?? "—" }}</span>
        <strong :title="member.username">{{ fullName(member) }}</strong>
        <span class="students-email">{{ member.email }}</span>
        <span v-if="ratingById.get(member.id)" class="students-rating">
          <b>{{ ratingById.get(member.id)!.total }}</b>
          <small>{{ ratingParts(ratingById.get(member.id)!) }}</small>
        </span>
        <span v-else class="students-rating">—</span>
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
  display: flex;
  flex-direction: column;
  min-height: 0;
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
  flex: 1 1 auto;
  min-height: 0;
  min-width: 860px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
.students-row {
  display: grid;
  grid-template-columns: 56px minmax(160px, 1fr) minmax(200px, 1.4fr) minmax(220px, 1.6fr) 110px;
  align-items: center;
  gap: 16px;
  min-height: 54px;
  padding: 0 16px;
  border-top: 1px solid #edf0f6;
  color: #1d2b43;
}
.students-row--head {
  position: sticky;
  top: 0;
  z-index: 1;
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
.students-place {
  color: #4a546b;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.students-rating {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 6px 0;
}
.students-rating b {
  font-variant-numeric: tabular-nums;
}
.students-rating small {
  color: #6c768a;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.students-rating-error {
  margin: 0;
  padding: 0 16px 12px;
  color: #9a3c3c;
  font-size: 13px;
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
