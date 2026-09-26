<script setup lang="ts">
import { computed, ref } from "vue";
import { LANGUAGES, type ProgrammingLanguage } from "../../languages";
import { useProgrammingEditor } from "./useProgrammingEditor";

const props = defineProps<{
  modelValue: string;
  language: ProgrammingLanguage;
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const host = ref<HTMLElement | null>(null);
const info = computed(() => LANGUAGES[props.language]);

const { mobile, editorFailed } = useProgrammingEditor({
  host,
  modelValue: () => props.modelValue,
  language: () => info.value.editor,
  disabled: () => Boolean(props.disabled),
  onChange: (value) => emit("update:modelValue", value),
});

function updateFromTextarea(event: Event): void {
  emit("update:modelValue", (event.target as HTMLTextAreaElement).value);
}
</script>

<template>
  <div class="programming-editor">
    <div class="programming-editor-bar">
      <span class="programming-editor-dot" />
      {{ info.title }}
      <span class="programming-editor-file">{{ info.fileName }}</span>
    </div>

    <textarea
      v-if="mobile || editorFailed"
      class="programming-editor-mobile"
      :value="modelValue"
      :disabled="disabled"
      :aria-label="`Код решения на ${info.title}`"
      spellcheck="false"
      @input="updateFromTextarea"
    />

    <div
      v-else
      ref="host"
      class="programming-editor-host"
      :aria-label="`Код решения на ${info.title}`"
    />
  </div>
</template>

<style scoped>
.programming-editor {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #dce3ef;
  border-radius: 14px;
  background: #fff;
}

.programming-editor-bar {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 42px;
  padding: 0 16px;
  border-bottom: 1px solid #e1e6f0;
  color: #52617a;
  font-size: var(--font-size-small);
  font-weight: 650;
}

.programming-editor-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3457f0;
}

.programming-editor-file {
  margin-left: auto;
  color: #8a94a8;
  font-family: var(--font-mono);
}

.programming-editor-host {
  width: 100%;
  height: 340px;
}

.programming-editor-mobile {
  display: block;
  box-sizing: border-box;
  width: 100%;
  min-height: 340px;
  resize: vertical;
  padding: 17px;
  border: 0;
  outline: 0;
  background: #fff;
  color: #0f172a;
  font: var(--font-size-small)/1.6 var(--font-mono);
}
</style>
