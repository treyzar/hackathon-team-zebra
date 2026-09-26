<script setup lang="ts">
import { deadlineLabel } from "./presentation";
import type { CourseDeadlineState } from "./types";

defineProps<{
  state: CourseDeadlineState;
  draft: string | null;
  disabled: boolean;
}>();

const emit = defineEmits<{ update: [value: string | null] }>();
</script>

<template>
  <aside class="deadlines-side">
    <section class="deadlines-card deadlines-course-card">
      <h3>Дедлайн курса для группы</h3>
      <p>
        Итоговый срок: <strong>{{ deadlineLabel(state.effective_due_at) }}</strong>
      </p>
      <template v-if="draft !== null">
        <input
          type="datetime-local"
          :value="draft"
          :disabled="disabled"
          aria-label="Дедлайн курса для группы"
          @input="emit('update', ($event.target as HTMLInputElement).value)"
        />
        <button
          class="deadlines-remove-course"
          type="button"
          :disabled="disabled"
          @click="emit('update', null)"
        >
          Убрать срок группы
        </button>
      </template>
      <button
        v-else
        class="deadlines-add"
        type="button"
        :disabled="disabled"
        @click="emit('update', '')"
      >
        + задать срок для группы
      </button>
    </section>
    <section class="deadlines-card deadlines-help">
      <h3>Как это работает</h3>
      <p>
        Общий дедлайн курса подставляется автоматически. Срок для группы заменяет его, а сроки
        отдельных шагов имеют приоритет. Ученик видит итоговый срок в задании и получает уведомление
        при его изменении.
      </p>
    </section>
  </aside>
</template>
