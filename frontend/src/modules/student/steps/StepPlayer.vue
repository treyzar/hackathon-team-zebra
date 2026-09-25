<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from "vue";
import {
  getAnswer,
  getSubmission,
  getSubmissions,
  submitAnswer,
  uploadSubmissionFile,
} from "@/modules/student/courses/api";
import {
  blockReason,
  documentTitle,
  errorMessage,
  stepDocument,
  stepLabels,
  submissionLabel,
} from "@/modules/student/courses/presentation";
import RichContent from "@/modules/student/courses/RichContent.vue";
import type {
  ChoiceContent,
  FreeTextContent,
  ProgrammingContent,
  RichDocument,
  StudentStep,
  Submission,
} from "@/modules/student/courses/types";
import { buildAnswer } from "./answer";
const ProgrammingEditor = defineAsyncComponent(() => import("./ProgrammingEditor.vue"));

const props = defineProps<{ step: StudentStep; number: string }>();
const emit = defineEmits<{ refresh: [] }>();
const document = computed(() => stepDocument(props.step.type, props.step.content));
const title = computed(() => documentTitle(document.value, stepLabels[props.step.type]));
const bodyDocument = computed<RichDocument | null>(() => {
  if (!document.value) return null;
  const first = document.value.content?.[0];
  return first?.type === "heading"
    ? { ...document.value, content: document.value.content?.slice(1) }
    : document.value;
});
const choice = computed(() => props.step.content as unknown as ChoiceContent);
const freeText = computed(() => props.step.content as unknown as FreeTextContent);
const programming = computed(() => props.step.content as unknown as ProgrammingContent);
const selected = ref<string[]>([]);
const answerText = ref("");
const code = ref("");
const files = ref<{ id: number; name: string }[]>([]);
const submissions = ref<Submission[]>([]);
const revealed = ref<Record<string, unknown> | null>(null);
const loading = ref(true);
const saving = ref(false);
const uploading = ref(false);
const error = ref("");
let pollTimer: ReturnType<typeof setTimeout> | null = null;
let active = true;

const latest = computed(() => submissions.value[0] ?? null);
const blocked = computed(
  () => loading.value || saving.value || uploading.value || !props.step.can_submit,
);
const remaining = computed(() =>
  props.step.max_attempts == null
    ? null
    : Math.max(0, props.step.max_attempts - props.step.attempts_used),
);
const sampleResults = computed(() => {
  const value = latest.value?.result_details.samples;
  return Array.isArray(value)
    ? (value as {
        input?: string;
        expected?: string;
        stdout?: string;
        stderr?: string;
        verdict?: string;
      }[])
    : [];
});
const testGroups = computed(() => {
  const value = latest.value?.result_details.groups;
  return Array.isArray(value)
    ? (value as {
        name?: string;
        passed?: boolean;
        earned?: number;
        points?: number;
        tests?: { verdict?: string }[];
      }[])
    : [];
});
const correctChoices = computed(() => {
  const answer = revealed.value;
  if (!answer) return [];
  if (typeof answer.correct === "string") return [answer.correct];
  return Array.isArray(answer.correct) ? (answer.correct as string[]) : [];
});
const referenceSolution = computed(() =>
  typeof revealed.value?.reference_solution === "string" ? revealed.value.reference_solution : "",
);
const referenceDocument = computed(() => {
  const value = revealed.value?.reference;
  return value && typeof value === "object" && (value as RichDocument).type === "doc"
    ? (value as RichDocument)
    : null;
});

function restoreAnswer(submission: Submission | undefined): void {
  const answer = submission?.answer;
  if (props.step.type === "programming")
    code.value =
      typeof answer?.code === "string" ? answer.code : (programming.value.template ?? "");
  if (props.step.type === "single_choice" && typeof answer?.option_id === "string")
    selected.value = [answer.option_id];
  if (props.step.type === "multiple_choice" && Array.isArray(answer?.option_ids))
    selected.value = answer.option_ids as string[];
  if (props.step.type === "free_text") {
    answerText.value = typeof answer?.text === "string" ? answer.text : "";
    if (Array.isArray(answer?.files))
      files.value = (answer.files as number[]).map((id) => ({ id, name: `Файл #${id}` }));
  }
}

async function loadSubmissions(): Promise<void> {
  loading.value = true;
  try {
    submissions.value = await getSubmissions(props.step.id);
    restoreAnswer(submissions.value[0]);
    schedulePoll();
  } catch (cause) {
    error.value = errorMessage(cause);
  } finally {
    loading.value = false;
  }
}

function schedulePoll(): void {
  if (pollTimer) clearTimeout(pollTimer);
  if (!latest.value || !["queued", "running"].includes(latest.value.status)) return;
  pollTimer = setTimeout(async () => {
    if (!active || !latest.value) return;
    try {
      const result = await getSubmission(latest.value.id);
      if (!active) return;
      submissions.value = [result, ...submissions.value.slice(1)];
      if (!["queued", "running"].includes(result.status)) emit("refresh");
      schedulePoll();
    } catch {
      if (active) pollTimer = setTimeout(schedulePoll, 5000);
    }
  }, 2500);
}

function toggleOption(id: string): void {
  if (props.step.type === "single_choice") selected.value = [id];
  else
    selected.value = selected.value.includes(id)
      ? selected.value.filter((item) => item !== id)
      : [...selected.value, id];
}

async function addFiles(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const picked = [...(input.files ?? [])];
  input.value = "";
  if (files.value.length + picked.length > freeText.value.max_files) {
    error.value = `Можно приложить не больше ${freeText.value.max_files} файлов.`;
    return;
  }
  error.value = "";
  uploading.value = true;
  try {
    for (const file of picked) {
      if (freeText.value.allowed_mime.length && !freeText.value.allowed_mime.includes(file.type))
        throw new Error(`Формат файла «${file.name}» не разрешён.`);
      files.value.push({ id: await uploadSubmissionFile(file), name: file.name });
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : errorMessage(cause);
  } finally {
    uploading.value = false;
  }
}

async function submit(): Promise<void> {
  if (blocked.value) return;
  const answer = buildAnswer(props.step.type, props.step.content, {
    selected: selected.value,
    text: answerText.value,
    files: files.value.map((file) => file.id),
    code: code.value,
  });
  if (!answer) {
    error.value =
      props.step.type === "free_text"
        ? "Заполните ответ и приложите необходимые файлы."
        : "Введите ответ перед отправкой.";
    return;
  }
  error.value = "";
  saving.value = true;
  try {
    const submission = await submitAnswer(props.step.id, answer);
    submissions.value = [submission, ...submissions.value];
    emit("refresh");
    schedulePoll();
  } catch (cause) {
    error.value = errorMessage(cause);
  } finally {
    saving.value = false;
  }
}

async function revealAnswer(): Promise<void> {
  error.value = "";
  try {
    revealed.value = await getAnswer(props.step.id);
  } catch (cause) {
    error.value = errorMessage(cause);
  }
}

onMounted(loadSubmissions);
onBeforeUnmount(() => {
  active = false;
  if (pollTimer) clearTimeout(pollTimer);
});
</script>

<template>
  <article class="student-lesson">
    <div class="student-lesson-meta">
      {{ stepLabels[step.type] }} · шаг {{ number }}
      <span v-if="step.deadline"
        >· до {{ new Date(step.deadline.due_at).toLocaleDateString("ru-RU") }}</span
      >
    </div>
    <h2>{{ title }}</h2>
    <div class="student-lesson-details">
      <span v-if="step.max_score"
        >{{ step.max_score }} балл{{ step.max_score === 1 ? "" : "ов" }}</span
      >
      <span v-if="remaining !== null">{{ remaining }} попыток осталось</span>
      <span v-if="step.progress.from_previous_version">Результат предыдущей версии учтён</span>
    </div>
    <section v-if="bodyDocument?.content?.length" class="student-paper">
      <RichContent :document="bodyDocument" />
    </section>
    <section v-if="loading" class="student-paper student-muted" role="status">
      Загружаем историю решений…
    </section>
    <section v-else class="student-answer-card">
      <h3>{{ step.type === "theory" ? "Готовы двигаться дальше?" : "Ваш ответ" }}</h3>
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
            @change="toggleOption(option.id)"
          />
          <span>{{ option.text }}</span>
        </label>
      </div>
      <div v-else-if="step.type === 'free_text'" class="student-free-answer">
        <label for="student-answer-text">Напишите ответ</label>
        <textarea
          id="student-answer-text"
          v-model="answerText"
          rows="7"
          :disabled="blocked"
          placeholder="Введите ответ здесь…"
        />
        <div v-if="freeText.max_files" class="student-file-area">
          <label class="student-file-button">
            <input
              type="file"
              multiple
              :accept="freeText.allowed_mime.join(',')"
              :disabled="blocked"
              @change="addFiles"
            />
            + Прикрепить файлы
          </label>
          <span class="student-muted"
            >От {{ freeText.min_files }} до {{ freeText.max_files }} файлов</span
          >
          <div v-for="file in files" :key="file.id" class="student-attached-file">
            <span>📎 {{ file.name }}</span>
            <button
              v-if="step.can_submit"
              type="button"
              :aria-label="`Убрать ${file.name}`"
              @click="files = files.filter((item) => item.id !== file.id)"
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
          Python 3 · {{ programming.time_limit_ms }} мс · {{ programming.memory_limit_mb }} МБ
        </p>
        <ProgrammingEditor v-model="code" :disabled="!step.can_submit" />
      </div>
      <div v-if="error" class="student-alert student-alert--error" role="alert">{{ error }}</div>
      <div class="student-submit-row">
        <button
          v-if="step.can_submit"
          class="student-submit-button"
          type="button"
          :disabled="blocked"
          @click="submit"
        >
          {{
            saving
              ? "Отправляем…"
              : step.type === "theory"
                ? "Отметить прочитанным"
                : latest
                  ? "Отправить снова"
                  : "Отправить на проверку"
          }}
        </button>
        <p v-else class="student-muted">{{ blockReason(step.submit_block_reason) }}</p>
      </div>
    </section>
    <section
      v-if="latest"
      class="student-result"
      :class="`student-result--${latest.status}`"
      aria-live="polite"
    >
      <div class="student-result-head">
        <strong>{{ submissionLabel(latest.status) }}</strong>
        <span v-if="latest.score !== null">{{ latest.score }} / {{ step.max_score }} баллов</span>
      </div>
      <p v-if="latest.review_comment">{{ latest.review_comment }}</p>
      <p v-if="latest.is_late" class="student-muted">Решение отправлено после срока.</p>
      <div v-if="sampleResults.length" class="student-test-results">
        <h4>Примеры</h4>
        <div v-for="(sample, index) in sampleResults" :key="index" class="student-test-row">
          <strong
            >Пример {{ index + 1 }} ·
            {{ sample.verdict === "ok" ? "верно" : sample.verdict }}</strong
          >
          <div v-if="sample.stdout != null">
            <span>Вывод программы:</span>
            <pre>{{ sample.stdout }}</pre>
          </div>
          <div v-if="sample.stderr">
            <span>Ошибки:</span>
            <pre>{{ sample.stderr }}</pre>
          </div>
        </div>
      </div>
      <div v-if="testGroups.length" class="student-test-results">
        <h4>Скрытые тесты</h4>
        <div v-for="(group, index) in testGroups" :key="index" class="student-group-result">
          <span
            >{{ group.name || `Группа ${index + 1}` }} ·
            {{ group.passed ? "пройдена" : "не пройдена" }}</span
          >
          <strong v-if="group.points != null">{{ group.earned ?? 0 }} / {{ group.points }}</strong>
        </div>
      </div>
    </section>
    <section v-if="step.answer_available" class="student-answer-reveal">
      <button v-if="!revealed" type="button" @click="revealAnswer">
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
  </article>
</template>

<style scoped>
.student-lesson {
  width: 100%;
  max-width: 980px;
  min-width: 0;
}
.student-lesson-meta {
  margin-bottom: 11px;
  color: #5e677d;
  font-size: 14px;
}
.student-lesson h2 {
  margin: 0 0 11px;
  color: #0f172a;
  font-size: clamp(29px, 3vw, 38px);
  font-weight: 800;
  line-height: 1.15;
}
.student-lesson-details {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 21px;
}
.student-lesson-details span {
  padding: 5px 11px;
  border-radius: 999px;
  background: #eaf0fe;
  color: #3457f0;
  font-size: 12px;
  font-weight: 700;
}
.student-paper,
.student-answer-card {
  min-width: 0;
  margin-bottom: 17px;
  padding: 25px 28px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.student-answer-card h3,
.student-answer-reveal h3 {
  margin: 0 0 17px;
  color: #0f172a;
  font-size: 20px;
}
.student-muted {
  margin: 0;
  color: #69758b;
  font-size: 14px;
}
.student-options {
  display: grid;
  gap: 10px;
}
.student-option {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 54px;
  padding: 12px 15px;
  border: 1px solid #dce3ef;
  border-radius: 11px;
  cursor: pointer;
}
.student-option:hover {
  border-color: #a6b8ff;
}
.student-option input {
  width: 18px;
  height: 18px;
  flex: none;
  accent-color: #3457f0;
}
.student-option--selected {
  border-color: #3457f0;
  background: #f3f6ff;
}
.student-option--correct {
  border-color: #62b987;
  background: #e4f5ec;
}
.student-free-answer {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.student-free-answer > label {
  font-weight: 650;
}
.student-free-answer textarea {
  width: 100%;
  min-height: 145px;
  resize: vertical;
  padding: 15px;
  border: 1px solid #dce3ef;
  border-radius: 12px;
  outline: none;
  font: inherit;
}
.student-free-answer textarea:focus {
  border-color: #3457f0;
  box-shadow: 0 0 0 3px #eaf0fe;
}
.student-file-area {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
}
.student-file-button {
  display: inline-flex;
  align-items: center;
  min-height: 41px;
  padding: 0 15px;
  border: 1px solid #dce3ef;
  border-radius: 10px;
  background: #fff;
  color: #3457f0;
  font-weight: 700;
  cursor: pointer;
}
.student-file-button input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}
.student-attached-file {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 11px;
  border-radius: 9px;
  background: #f4f6fb;
  color: #43516b;
  font-size: 13px;
}
.student-attached-file button {
  color: #a54343;
  font-size: 20px;
}
.student-programming {
  display: grid;
  gap: 16px;
}
.student-samples {
  display: grid;
  gap: 10px;
}
.student-samples h4,
.student-test-results h4 {
  margin: 0;
  font-size: 16px;
}
.student-sample {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 13px;
  border: 1px solid #e2e7f0;
  border-radius: 11px;
  background: #f9faff;
}
.student-sample > strong {
  grid-column: 1 / -1;
  color: #27344d;
}
.student-sample span,
.student-test-row span {
  color: #68748a;
  font-size: 12px;
}
.student-sample pre,
.student-test-row pre,
.student-answer-reveal pre {
  max-width: 100%;
  overflow: auto;
  margin: 5px 0 0;
  padding: 10px;
  border-radius: 8px;
  background: #eef1f8;
  color: #25324a;
  font:
    13px/1.55 ui-monospace,
    SFMono-Regular,
    Menlo,
    monospace;
}
.student-alert {
  margin-top: 15px;
  padding: 11px 14px;
  border-radius: 10px;
}
.student-alert--error {
  background: #fcebeb;
  color: #a53b3b;
}
.student-submit-row {
  display: flex;
  align-items: center;
  min-height: 54px;
  margin-top: 20px;
}
.student-submit-button {
  min-height: 54px;
  padding: 0 26px;
  border: 0;
  border-radius: 13px;
  background: #3457f0;
  color: #fff;
  font:
    700 16px Onest,
    sans-serif;
  cursor: pointer;
}
.student-submit-button:hover:not(:disabled) {
  background: #2446d4;
}
.student-submit-button:disabled {
  cursor: wait;
  opacity: 0.6;
}
.student-result {
  margin: 16px 0;
  padding: 17px 20px;
  border-radius: 13px;
  background: #fff1e6;
  color: #7c400f;
}
.student-result--correct,
.student-result--accepted {
  background: #e4f5ec;
  color: #166d45;
}
.student-result--queued,
.student-result--running,
.student-result--pending_review {
  background: #efebfe;
  color: #6045bd;
}
.student-result--error {
  background: #fcebeb;
  color: #a53b3b;
}
.student-result-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 16px;
}
.student-result p {
  margin: 11px 0 0;
}
.student-test-results {
  display: grid;
  gap: 8px;
  margin-top: 19px;
  padding-top: 14px;
  border-top: 1px solid #d9dde8;
}
.student-test-row {
  display: grid;
  gap: 7px;
  padding: 10px;
  border-radius: 9px;
  background: #ffffffb8;
}
.student-test-row > div {
  min-width: 0;
}
.student-group-result {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 9px;
  background: #ffffffb8;
  font-size: 13px;
}
.student-answer-reveal {
  padding: 17px 20px;
  border: 1px solid #dbe6df;
  border-radius: 13px;
  background: #f1f9f4;
}
.student-answer-reveal button {
  color: #17915a;
  font-weight: 750;
}
.student-answer-reveal ul {
  margin: 0;
  padding-left: 22px;
}
@media (max-width: 680px) {
  .student-paper,
  .student-answer-card {
    padding: 19px;
  }
  .student-sample {
    grid-template-columns: 1fr;
  }
}
</style>
