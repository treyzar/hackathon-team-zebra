import { nextTick, onBeforeUnmount, onMounted, type Ref, ref, watch } from "vue";
import * as monaco from "monaco-editor/editor/editor.api";
import "monaco-editor/languages/definitions/python/register";
import EditorWorker from "monaco-editor/editor/editor.worker?worker";

interface UseProgrammingEditorOptions {
  host: Ref<HTMLElement | null>;
  modelValue: () => string;
  disabled: () => boolean;
  onChange: (value: string) => void;
}

(
  globalThis as typeof globalThis & {
    MonacoEnvironment?: { getWorker: () => Worker };
  }
).MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
};

export function useProgrammingEditor(options: UseProgrammingEditorOptions) {
  const mobile = ref(false);
  const editorFailed = ref(false);

  let editor: monaco.editor.IStandaloneCodeEditor | null = null;
  let observer: ResizeObserver | null = null;

  function destroyEditor(): void {
    observer?.disconnect();
    observer = null;
    editor?.dispose();
    editor = null;
  }

  function createEditor(): void {
    if (mobile.value || !options.host.value || editor || editorFailed.value) return;

    try {
      editor = monaco.editor.create(options.host.value, {
        value: options.modelValue(),
        language: "python",
        theme: "vs",
        readOnly: options.disabled(),
        automaticLayout: false,
        minimap: { enabled: false },
        fontSize: 15,
        lineHeight: 24,
        tabSize: 4,
        scrollBeyondLastLine: false,
        wordWrap: "on",
        padding: { top: 16, bottom: 16 },
      });

      editor.onDidChangeModelContent(() => {
        options.onChange(editor?.getValue() ?? "");
      });

      observer = new ResizeObserver(() => editor?.layout());
      observer.observe(options.host.value);
    } catch (cause) {
      console.error("Monaco initialization failed:", cause);
      destroyEditor();
      editorFailed.value = true;
    }
  }

  function updateViewport(): void {
    mobile.value = window.matchMedia("(max-width: 767px)").matches;
  }

  onMounted(() => {
    updateViewport();
    window.addEventListener("resize", updateViewport);
    createEditor();
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", updateViewport);
    destroyEditor();
  });

  watch(mobile, async (isMobile) => {
    if (isMobile) {
      destroyEditor();
      return;
    }

    await nextTick();
    createEditor();
  });

  watch(options.modelValue, (value) => {
    if (editor && editor.getValue() !== value) editor.setValue(value);
  });

  watch(options.disabled, (value) => {
    editor?.updateOptions({ readOnly: value });
  });

  return {
    mobile,
    editorFailed,
  };
}
