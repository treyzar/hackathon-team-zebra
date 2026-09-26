<script setup lang="ts">
import { computed } from "vue";
import RichContent from "@/modules/student/courses/RichContent.vue";
import type { ChoiceContent, RichDocument } from "@/modules/student/courses/types";

const props = defineProps<{
  choice: ChoiceContent;
  revealed: Record<string, unknown> | null;
  correctChoices: string[];
  referenceDocument: RichDocument | null;
  referenceSolution: string;
}>();

const emit = defineEmits<{ reveal: [] }>();

const acceptedAnswers = computed(() => {
  const accepted = props.revealed?.accepted;
  return Array.isArray(accepted)
    ? accepted.filter((value): value is string => typeof value === "string")
    : [];
});

const numberValue = computed(() => {
  const value = props.revealed?.value;
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  return "";
});
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
      <ul v-else-if="acceptedAnswers.length">
        <li v-for="answer in acceptedAnswers" :key="answer">{{ answer }}</li>
      </ul>
      <p v-else-if="numberValue">
        Правильный ответ: <strong>{{ numberValue }}</strong>
      </p>
      <RichContent v-else-if="referenceDocument" :document="referenceDocument" />
      <pre v-else-if="referenceSolution">{{ referenceSolution }}</pre>
      <p v-else>Ответ доступен в результате проверки.</p>
    </template>
  </section>
</template>
