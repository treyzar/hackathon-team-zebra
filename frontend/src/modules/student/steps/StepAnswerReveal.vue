<script setup lang="ts">
import RichContent from "@/modules/student/courses/RichContent.vue";
import type { ChoiceContent, RichDocument } from "@/modules/student/courses/types";

defineProps<{
  choice: ChoiceContent;
  revealed: Record<string, unknown> | null;
  correctChoices: string[];
  referenceDocument: RichDocument | null;
  referenceSolution: string;
}>();

const emit = defineEmits<{ reveal: [] }>();
</script>

<template>
  <section class="student-answer-reveal">
    <button v-if="!revealed" type="button" @click="emit('reveal')">
      Показать правильный ответ
    </button>

    <template v-else>
      <h3>Правильный ответ</h3>
      <ul v-if="correctChoices.length">
        <li
          v-for="option in choice.options.filter((item) => correctChoices.includes(item.id))"
          :key="option.id"
        >
          {{ option.text }}
        </li>
      </ul>
      <RichContent v-else-if="referenceDocument" :document="referenceDocument" />
      <pre v-else-if="referenceSolution">{{ referenceSolution }}</pre>
      <p v-else>Ответ доступен в результате проверки.</p>
    </template>
  </section>
</template>
