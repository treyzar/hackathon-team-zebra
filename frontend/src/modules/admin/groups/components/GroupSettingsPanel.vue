<script setup lang="ts">
import { ref, watch } from "vue";
import type { AdminUser, Group } from "../../shared/types";

const props = defineProps<{
  group: Group;
  curators: AdminUser[];
  busy: boolean;
}>();

const emit = defineEmits<{
  save: [payload: { name: string; curator_id: number | null }];
  delete: [];
}>();

const name = ref("");
const curatorId = ref<number | "">("");

watch(
  () => props.group,
  (group) => {
    name.value = group.name;
    curatorId.value = group.curator_id ?? "";
  },
  { immediate: true },
);

function submit(): void {
  const trimmed = name.value.trim();
  if (!trimmed || props.busy) return;
  emit("save", {
    name: trimmed,
    curator_id: curatorId.value === "" ? null : curatorId.value,
  });
}
</script>

<template>
  <form class="group-settings" @submit.prevent="submit">
    <label class="group-field group-field--name">
      <span>Название</span>
      <input v-model="name" maxlength="200" required />
    </label>

    <label class="group-field group-field--curator">
      <span>Куратор</span>
      <select v-model="curatorId">
        <option value="">Не назначен</option>
        <option v-for="user in curators" :key="user.id" :value="user.id">
          {{ user.username }}
        </option>
      </select>
    </label>

    <div class="group-settings__spacer" />
    <p class="group-settings__help">
      Куратор видит очередь работ и вопросы только своих групп
    </p>

    <div class="group-settings__actions">
      <button class="group-save" :disabled="busy">Сохранить</button>
      <button class="group-delete" type="button" :disabled="busy" @click="emit('delete')">
        Удалить
      </button>
    </div>
  </form>
</template>

<style scoped>
.group-settings {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}
.group-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #1d2b43;
  font-weight: 600;
}
.group-field--name {
  width: 220px;
}
.group-field--curator {
  width: 260px;
}
.group-field input,
.group-field select {
  width: 100%;
  height: 40px;
  box-sizing: border-box;
  padding: 0 12px;
  border: 1px solid #d9dfeb;
  border-radius: 10px;
  outline: none;
  background: #fff;
  color: #1d2b43;
  font: 400 14px Onest, system-ui, sans-serif;
}
.group-field input:focus,
.group-field select:focus {
  border-color: #3457f0;
  box-shadow: 0 0 0 3px rgba(52, 87, 240, 0.1);
}
.group-settings__spacer {
  flex: 1 1 24px;
}
.group-settings__help {
  max-width: 330px;
  margin: 0 0 8px;
  color: #4a546b;
  font-size: 13px;
}
.group-settings__actions {
  display: flex;
  gap: 8px;
  width: 100%;
}
.group-save,
.group-delete {
  height: 36px;
  padding: 0 13px;
  border-radius: 10px;
  font: 600 13px Onest, system-ui, sans-serif;
  cursor: pointer;
}
.group-save {
  border: 0;
  background: #3457f0;
  color: #fff;
}
.group-delete {
  border: 1px solid #e1e6f0;
  background: #fff;
  color: #b33a3a;
}
.group-save:disabled,
.group-delete:disabled {
  opacity: 0.55;
  cursor: default;
}
@media (max-width: 760px) {
  .group-field--name,
  .group-field--curator {
    width: 100%;
  }
  .group-settings__spacer {
    display: none;
  }
  .group-settings__help {
    max-width: none;
  }
}
</style>
