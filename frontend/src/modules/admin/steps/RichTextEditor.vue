<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import Quill from "quill";
import "quill/dist/quill.snow.css";
import { getApiErrorMessage } from "@/api/errors";
import { fileUrl, uploadContentImage } from "./file-api";
import { docImageIds, docToQuillOps, imageUrl, quillOpsToDoc } from "./quill-document";
import type { QuillOp } from "./quill-document";
import type { RichText } from "../shared/types";

const props = defineProps<{ modelValue: RichText; readonly?: boolean }>();
const emit = defineEmits<{
  "update:modelValue": [value: RichText];
  error: [message: string];
  validity: [valid: boolean];
  uploading: [active: boolean];
}>();
const editor = ref<HTMLElement | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
let quill: Quill | null = null;

function chooseImage(): void {
  fileInput.value?.click();
}

async function addImage(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || !quill) return;
  uploading.value = true;
  emit("uploading", true);
  try {
    const uploaded = await uploadContentImage(file);
    const index = quill.getSelection(true)?.index ?? quill.getLength() - 1;
    quill.insertEmbed(index, "image", imageUrl(uploaded.url, uploaded.id), "user");
    quill.setSelection(index + 1, 0, "user");
  } catch (cause) {
    emit("validity", false);
    emit("error", getApiErrorMessage(cause));
  } finally {
    uploading.value = false;
    emit("uploading", false);
  }
}

onMounted(async () => {
  if (!editor.value) return;
  quill = new Quill(editor.value, {
    theme: "snow",
    placeholder: "Введите текст шага…",
    modules: {
      toolbar: props.readonly
        ? false
        : {
            container: [
              [{ header: [1, 2, false] }],
              ["bold", "italic", "underline"],
              [{ list: "ordered" }, { list: "bullet" }],
              ["link", "image"],
              ["clean"],
            ],
            handlers: { image: chooseImage },
          },
    },
  });
  const instance = quill;
  instance.enable(false);
  try {
    const ids = docImageIds(props.modelValue);
    const urls = new Map(
      await Promise.all(ids.map(async (id) => [id, await fileUrl(id)] as const)),
    );
    if (quill !== instance) return;
    instance.setContents(docToQuillOps(props.modelValue, urls), "silent");
  } catch (cause) {
    emit("validity", false);
    emit("error", getApiErrorMessage(cause));
  }
  if (quill !== instance) return;
  instance.enable(!props.readonly);
  if (props.readonly) return;
  instance.on("text-change", () => {
    try {
      emit("update:modelValue", quillOpsToDoc(instance.getContents().ops as QuillOp[]));
      emit("validity", true);
    } catch (cause) {
      emit("validity", false);
      emit("error", cause instanceof Error ? cause.message : getApiErrorMessage(cause));
    }
  });
});

onBeforeUnmount(() => {
  quill = null;
});
</script>

<template>
  <div class="quill-editor">
    <div ref="editor" />
    <input
      v-if="!readonly"
      ref="fileInput"
      class="image-input"
      type="file"
      accept="image/*"
      aria-label="Выбрать изображение"
      @change="addImage"
    />
    <p v-if="uploading" class="admin-muted" role="status">Загружаем изображение…</p>
  </div>
</template>

<style scoped>
.quill-editor {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}
.image-input {
  display: none;
}
.quill-editor :deep(.ql-toolbar) {
  display: flex;
  flex-wrap: wrap;
  width: 100%;
  max-width: 100%;
  border-color: #e1e6f0;
  border-radius: 10px 10px 0 0;
  background: #f4f6fb;
}
.quill-editor :deep(.ql-toolbar .ql-formats) {
  flex: none;
}
.quill-editor :deep(.ql-container) {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  height: auto;
  min-height: var(--quill-editor-min-height, 320px);
  border-color: #e1e6f0;
  border-radius: 0 0 10px 10px;
  background: #fff;
  font-family: inherit;
  font-size: 14px;
}
.quill-editor :deep(.ql-editor) {
  width: 100%;
  max-width: 100%;
  height: auto;
  min-height: var(--quill-editor-min-height, 320px);
  padding: 22px 24px;
  line-height: 1.7;
  overflow-wrap: anywhere;
  overflow-x: auto;
}
.quill-editor :deep(.ql-editor pre),
.quill-editor :deep(.ql-code-block-container) {
  max-width: 100%;
  overflow-x: auto;
}
.quill-editor :deep(.ql-editor img) {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 12px 0;
  border-radius: 8px;
}
.quill-editor :deep(.ql-editor:focus) {
  outline: 2px solid #3457f0;
  outline-offset: -2px;
}
.quill-editor :deep(.ql-tooltip) {
  box-sizing: border-box;
  max-width: calc(100% - 16px);
  white-space: normal;
  overflow-wrap: anywhere;
}
</style>
