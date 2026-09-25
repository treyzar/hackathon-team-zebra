<script setup lang="ts">
import { ref } from "vue";
import type { AdminUser } from "../../shared/types";

const props = defineProps<{
  curators: AdminUser[];
  busy: boolean;
}>();

const emit = defineEmits<{
  create: [payload: { name: string; curator_id: number | null }];
  cancel: [];
}>();

const name = ref("");
const curatorId = ref<number | "">("");

function submit(): void {
  const trimmed = name.value.trim();
  if (!trimmed || props.busy) return;

  emit("create", {
    name: trimmed,
    curator_id: curatorId.value === "" ? null : curatorId.value,
  });
}
</script>

<template>
  <section class="admin-panel">
    <div class="admin-panel-head">
      <div>
        <h2>Новая группа</h2>
        <p>Куратора можно назначить позже.</p>
      </div>
    </div>

    <form class="admin-form" @submit.prevent="submit">
      <div class="admin-form-row">
        <label class="admin-field">
          Название
          <input v-model="name" maxlength="200" required placeholder="Например, 5А" />
        </label>
        <label class="admin-field">
          Куратор
          <select v-model="curatorId">
            <option value="">Не назначен</option>
            <option v-for="user in curators" :key="user.id" :value="user.id">
              {{ user.username }}
            </option>
          </select>
        </label>
      </div>

      <div class="admin-actions">
        <button class="admin-button admin-button--primary" :disabled="busy">Создать</button>
        <button class="admin-button" type="button" :disabled="busy" @click="emit('cancel')">
          Отмена
        </button>
      </div>
    </form>
  </section>
</template>
