<script setup lang="ts">
import type {
  ChoiceContent,
  FreeTextContent,
  ProgrammingContent,
  StudentStep,
} from "@/modules/student/courses/types";
import { LANGUAGES, type ProgrammingLanguage } from "../../languages";
import ProgrammingEditor from "./ProgrammingEditor.vue";
import type { AttachedFile } from "./useStepPlayer";

const props = defineProps<{
  step: StudentStep;
  choice: ChoiceContent;
  freeText: FreeTextContent;
  programming: ProgrammingContent;
  selected: string[];
  answerText: string;
  code: string;
  languages: ProgrammingLanguage[];
  language: ProgrammingLanguage;
  files: AttachedFile[];
  correctChoices: string[];
  blocked: boolean;
}>();

const emit = defineEmits<{
  toggleOption: [id: string];
  addFiles: [event: Event];
  removeFile: [id: number];
  "update:answerText": [value: string];
  "update:code": [value: string];
  "update:language": [value: ProgrammingLanguage];
}>();
const numberContent = computed(() => props.step.content as unknown as NumberContent);
</script>

<template>
  <p v-if="step.type === 'theory'" class="student-muted">
    Прочитайте материал и отметьте шаг выполненным.
  </p>

  <div
    v-else-if="step.type === 'single_choice' || step.type === 'multiple_choice'"
    class="student-options"
    role="group"
    aria-label="Варианты ответа"
  >
    <label
      v-for="option in choice.options"
      :key="option.id"
      class="student-option"
      :class="{
        'student-option--selected': selected.includes(option.id),
        'student-option--correct': correctChoices.includes(option.id),
      }"
    >
      <input
        :type="step.type === 'single_choice' ? 'radio' : 'checkbox'"
        :name="`step-${step.id}`"
        :checked="selected.includes(option.id)"
        :disabled="blocked"
        @change="emit('toggleOption', option.id)"
      />
      <span>{{ option.text }}</span>
    </label>
  </div>

  <div v-else-if="step.type === 'free_text'" class="student-free-answer">
    <label for="student-answer-text">Напишите ответ</label>
    <textarea
      id="student-answer-text"
      :value="answerText"
      rows="7"
      :disabled="blocked"
      placeholder="Введите ответ здесь…"
      @input="emit('update:answerText', ($event.target as HTMLTextAreaElement).value)"
    />

    <div v-if="freeText.max_files" class="student-file-area">
      <label class="student-file-button">
        <input
          type="file"
          multiple
          :accept="freeText.allowed_mime.join(',')"
          :disabled="blocked"
          @change="emit('addFiles', $event)"
        />
        + Прикрепить файлы
      </label>

      <span class="student-muted">
        От {{ freeText.min_files }} до {{ freeText.max_files }} файлов
      </span>

      <div v-for="file in files" :key="file.id" class="student-attached-file">
        <span>📎 {{ file.name }}</span>
        <button
          v-if="step.can_submit"
          type="button"
          :aria-label="`Убрать ${file.name}`"
          @click="emit('removeFile', file.id)"
        >
          ×
        </button>
      </div>
    </div>
  </div>

  <div v-else-if="step.type === 'programming'" class="student-programming">
    <div v-if="programming.samples.length" class="student-samples">
      <h4>Примеры</h4>
      <div v-for="(sample, index) in programming.samples" :key="index" class="student-sample">
        <strong>Пример {{ index + 1 }}</strong>
        <div>
          <span>Ввод</span>
          <pre>{{ sample.input || "Нет входных данных" }}</pre>
        </div>
        <div>
          <span>Вывод</span>
          <pre>{{ sample.output }}</pre>
        </div>
      </div>
    </div>

    <p class="student-muted">
      {{ programming.time_limit_ms }} мс · {{ programming.memory_limit_mb }} МБ
    </p>

    <label v-if="languages.length > 1" class="student-language">
      Язык
      <select
        :value="language"
        :disabled="blocked"
        @change="
          emit('update:language', ($event.target as HTMLSelectElement).value as ProgrammingLanguage)
        "
      >
        <option v-for="key in languages" :key="key" :value="key">
          {{ LANGUAGES[key].title }}
        </option>
      </select>
    </label>

    <ProgrammingEditor
      :model-value="code"
      :language="language"
      :disabled="blocked"
      @update:model-value="emit('update:code', $event)"
    />
  </div>
    <div v-else-if="step.type === 'short_text'" class="student-short-answer">
    <label for="student-short-text">Ответ</label>
    <input
      id="student-short-text"
      type="text"
      :value="answerText"
      maxlength="500"
      :disabled="blocked"
      placeholder="Введите короткий ответ"
      @input="emit('update:answerText', ($event.target as HTMLInputElement).value)"
    />
    <span class="student-muted">До 500 символов.</span>
  </div>

  <div v-else-if="step.type === 'number'" class="student-number-answer">
    <label for="student-number-text">
      {{ numberContent.kind === "decimal" ? "Число" : "Целое число" }}
    </label>
    <input
      id="student-number-text"
      type="text"
      inputmode="decimal"
      :value="answerText"
      maxlength="40"
      :disabled="blocked"
      :placeholder="numberContent.kind === 'decimal' ? 'Например, 3,14' : 'Например, 42'"
      @input="emit('update:answerText', ($event.target as HTMLInputElement).value)"
    />
    <span class="student-muted">
      <template v-if="numberContent.kind === 'decimal'">
        Можно ввести точку или запятую. Округлите до
        {{ numberContent.precision }}
        {{ numberContent.precision === 1 ? "знака" : "знаков" }} после запятой.
      </template>
      <template v-else>Только целое число, без дробной части.</template>
    </span>
  </div>
</template>
