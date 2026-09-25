<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as monaco from "monaco-editor/editor/editor.api";
import "monaco-editor/languages/definitions/python/register";
import EditorWorker from "monaco-editor/editor/editor.worker?worker";

const props = defineProps<{ modelValue: string; disabled?: boolean }>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const host = ref<HTMLElement | null>(null);
const mobile = ref(false);
let editor: monaco.editor.IStandaloneCodeEditor | null = null;
let observer: ResizeObserver | null = null;

(
  globalThis as typeof globalThis & { MonacoEnvironment?: { getWorker: () => Worker } }
).MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
};

function createEditor(): void {
  if (mobile.value || !host.value || editor) return;
  editor = monaco.editor.create(host.value, {
    value: props.modelValue,
    language: "python",
    theme: "vs",
    readOnly: props.disabled,
    automaticLayout: false,
    minimap: { enabled: false },
    fontSize: 15,
    lineHeight: 24,
    tabSize: 4,
    scrollBeyondLastLine: false,
    wordWrap: "on",
    padding: { top: 16, bottom: 16 },
  });
  editor.onDidChangeModelContent(() => emit("update:modelValue", editor?.getValue() ?? ""));
  observer = new ResizeObserver(() => editor?.layout());
  observer.observe(host.value);
}

function destroyEditor(): void {
  observer?.disconnect();
  observer = null;
  editor?.dispose();
  editor = null;
}

function updateLayout(): void {
  mobile.value = window.matchMedia("(max-width: 767px)").matches;
}

onMounted(() => {
  updateLayout();
  window.addEventListener("resize", updateLayout);
  createEditor();
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateLayout);
  destroyEditor();
});
watch(mobile, async (isMobile) => {
  if (isMobile) destroyEditor();
  else {
    await nextTick();
    createEditor();
  }
});
watch(
  () => props.modelValue,
  (value) => {
    if (editor && editor.getValue() !== value) editor.setValue(value);
  },
);
watch(
  () => props.disabled,
  (value) => editor?.updateOptions({ readOnly: value }),
);
</script>

<template>
  <div class="programming-editor">
    <div class="programming-editor-bar">
      <span class="programming-editor-dot" /> Python 3
      <span class="programming-editor-file">main.py</span>
    </div>
    <textarea
      v-if="mobile"
      class="programming-editor-mobile"
      :value="modelValue"
      :disabled="disabled"
      aria-label="Код решения на Python"
      spellcheck="false"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    />
    <div v-else ref="host" class="programming-editor-host" aria-label="Код решения на Python" />
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
  font-size: 13px;
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
  font-family: monospace;
}
.programming-editor-host {
  width: 100%;
  height: 340px;
}
.programming-editor-mobile {
  display: block;
  width: 100%;
  min-height: 340px;
  resize: vertical;
  padding: 17px;
  border: 0;
  outline: 0;
  background: #fff;
  color: #0f172a;
  font:
    14px/1.6 ui-monospace,
    SFMono-Regular,
    Menlo,
    monospace;
}
</style>
