import { type ProgrammingLanguage, stepLanguages } from "../../languages";
import { docToText, textToDoc } from "../shared/format";
import { hasDocContent } from "./quill-document";
import type { RichText, Step, StepPayload, StepType } from "../shared/types";

export interface ChoiceOption {
  id: string;
  text: string;
  correct: boolean;
}
export interface CodeSample {
  input: string;
  output: string;
  input_file?: number | null;
  output_file?: number | null;
}
export interface TestGroup {
  name: string;
  points: number;
  tests: CodeSample[];
}

export interface StepForm {
  type: StepType;
  title: string;
  body: RichText;
  maxScore: number;
  maxAttempts: number | "" | null;
  showAnswer: string;
  options: ChoiceOption[];
  scoring: string;
  requireText: boolean;
  minFiles: number;
  maxFiles: number;
  allowedMime: string;
  criteria: string;
  reference: string;
  originalReference: RichText | null;
  referenceFiles: number[];
  grading: string;
  // The first one is the default for the student.
  languages: ProgrammingLanguage[];
  timeLimitMs: number;
  memoryLimitMb: number;
  template: string;
  samples: CodeSample[];
  testGroups: TestGroup[];
  referenceSolution: string;
}

export function newStepForm(type: StepType = "theory"): StepForm {
  return {
    type,
    title: "",
    body: textToDoc(""),
    maxScore: type === "theory" ? 0 : 1,
    maxAttempts: null,
    showAnswer: "never",
    options: [
      { id: crypto.randomUUID(), text: "", correct: true },
      { id: crypto.randomUUID(), text: "", correct: false },
    ],
    scoring: "all_or_nothing",
    requireText: true,
    minFiles: 0,
    maxFiles: 0,
    allowedMime: "",
    criteria: "",
    reference: "",
    originalReference: null,
    referenceFiles: [],
    grading: "tests",
    languages: ["python3"],
    timeLimitMs: 2000,
    memoryLimitMb: 256,
    template: "",
    samples: [],
    testGroups: [{ name: "Основная группа", points: 1, tests: [{ input: "", output: "" }] }],
    referenceSolution: "",
  };
}

function object(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function document(value: unknown): RichText {
  const data = object(value);
  return data.type === "doc" && Array.isArray(data.content) ? (data as RichText) : textToDoc("");
}

function reuseDocument(text: string, original: RichText | null): RichText {
  return original && docToText(original) === text ? original : textToDoc(text);
}

function splitTitle(doc: RichText): { title: string; body: RichText } {
  const [first, ...rest] = doc.content;
  const attrs = first?.attrs as Record<string, unknown> | undefined;
  if (first?.type !== "heading" || attrs?.zebra_title !== true) return { title: "", body: doc };
  const content = Array.isArray(first.content) ? first.content : [];
  const title = content
    .map((item) => String((item as Record<string, unknown>).text ?? ""))
    .join("");
  return { title, body: { type: "doc", content: rest.length ? rest : [{ type: "paragraph" }] } };
}

function withTitle(title: string, body: RichText): RichText {
  if (!title.trim()) return body;
  return {
    type: "doc",
    content: [
      {
        type: "heading",
        attrs: { level: 1, zebra_title: true },
        content: [{ type: "text", text: title.trim() }],
      },
      ...body.content,
    ],
  };
}

export function formFromStep(step: Step): StepForm {
  const form = newStepForm(step.type);
  const { content, answer_key: answerKey, settings } = step.revision;
  const body = document(content.body ?? content.question ?? content.statement);
  const titled = splitTitle(body);
  form.title = titled.title;
  form.body = titled.body;
  form.maxScore = step.revision.max_score;
  form.maxAttempts = typeof settings.max_attempts === "number" ? settings.max_attempts : null;
  form.showAnswer = String(settings.show_answer ?? "never");
  form.scoring = String(settings.scoring ?? "all_or_nothing");
  if (step.type === "single_choice" || step.type === "multiple_choice") {
    const correct = answerKey.correct;
    const ids = new Set(Array.isArray(correct) ? correct.map(String) : [String(correct)]);
    form.options = (Array.isArray(content.options) ? content.options : []).map((item) => {
      const option = object(item);
      return {
        id: String(option.id),
        text: String(option.text ?? ""),
        correct: ids.has(String(option.id)),
      };
    });
  }
  if (step.type === "free_text") {
    form.requireText = Boolean(content.require_text);
    form.minFiles = Number(content.min_files ?? 0);
    form.maxFiles = Number(content.max_files ?? 0);
    form.allowedMime = (Array.isArray(content.allowed_mime) ? content.allowed_mime : [])
      .map(String)
      .join(", ");
    form.criteria = String(answerKey.criteria ?? "");
    form.referenceFiles = (Array.isArray(answerKey.files) ? answerKey.files : []).map(Number);
    if (answerKey.reference) {
      form.originalReference = document(answerKey.reference);
      form.reference = docToText(form.originalReference);
    }
  }
  if (step.type === "programming") {
    form.grading = String(settings.grading ?? "tests");
    form.languages = stepLanguages(content);
    form.timeLimitMs = Number(content.time_limit_ms ?? 2000);
    form.memoryLimitMb = Number(content.memory_limit_mb ?? 256);
    form.template = String(content.template ?? "");
    form.samples = (Array.isArray(content.samples) ? content.samples : []).map((item) => {
      const sample = object(item);
      return { input: String(sample.input ?? ""), output: String(sample.output ?? "") };
    });
    form.testGroups = (Array.isArray(answerKey.test_groups) ? answerKey.test_groups : []).map(
      (item) => {
        const group = object(item);
        return {
          name: String(group.name ?? ""),
          points: Number(group.points ?? 0),
          tests: (Array.isArray(group.tests) ? group.tests : []).map((test) => {
            const data = object(test);
            return {
              input: String(data.input ?? ""),
              output: String(data.output ?? ""),
              input_file: data.input_file == null ? null : Number(data.input_file),
              output_file: data.output_file == null ? null : Number(data.output_file),
            };
          }),
        };
      },
    );
    form.referenceSolution = String(answerKey.reference_solution ?? "");
  }
  return form;
}

export function validateStepForm(form: StepForm): string | null {
  if (!hasDocContent(form.body)) return "Заполните содержание шага.";
  if (!Number.isInteger(form.maxScore) || form.maxScore < 0 || form.maxScore > 1000)
    return "Баллы должны быть от 0 до 1000.";
  if (
    form.maxAttempts !== null &&
    form.maxAttempts !== "" &&
    (!Number.isInteger(form.maxAttempts) || form.maxAttempts < 1)
  )
    return "Число попыток должно быть больше нуля.";
  if (form.type === "single_choice" || form.type === "multiple_choice") {
    if (form.options.length < 2 || form.options.some((option) => !option.text.trim()))
      return "Добавьте хотя бы два заполненных варианта ответа.";
    const correct = form.options.filter((option) => option.correct).length;
    if (correct !== 1 && form.type === "single_choice")
      return "Укажите ровно один правильный ответ.";
    if (!correct && form.type === "multiple_choice")
      return "Укажите хотя бы один правильный ответ.";
  }
  if (
    form.type === "free_text" &&
    (!Number.isInteger(form.minFiles) ||
      !Number.isInteger(form.maxFiles) ||
      form.minFiles < 0 ||
      form.minFiles > form.maxFiles ||
      form.maxFiles > 10)
  )
    return "Проверьте допустимое число файлов (от 0 до 10).";
  if (
    form.type === "programming" &&
    (!Number.isInteger(form.timeLimitMs) ||
      form.timeLimitMs < 100 ||
      form.timeLimitMs > 15000 ||
      !Number.isInteger(form.memoryLimitMb) ||
      form.memoryLimitMb < 16 ||
      form.memoryLimitMb > 512)
  )
    return "Проверьте ограничения времени и памяти.";
  if (form.type === "programming" && !form.languages.length)
    return "Выберите хотя бы один язык программирования.";
  if (form.type === "programming" && form.grading !== "manual") {
    if (
      !form.testGroups.length ||
      form.testGroups.some((group) => !group.name.trim() || !group.tests.length)
    )
      return "Для автоматической проверки нужна группа с тестами.";
    if (
      form.scoring === "per_group" &&
      form.testGroups.reduce((sum, group) => sum + group.points, 0) !== form.maxScore
    )
      return "Сумма баллов групп тестов должна равняться максимальному баллу шага.";
  }
  return null;
}

export function payloadFromForm(form: StepForm): StepPayload {
  const settings: Record<string, unknown> = {
    grading:
      form.type === "theory"
        ? "none"
        : form.type === "free_text"
          ? "manual"
          : form.type === "programming"
            ? form.grading
            : "auto",
    max_attempts: form.maxAttempts === "" ? null : form.maxAttempts,
    show_answer: form.showAnswer,
  };
  const body = withTitle(form.title, form.body);
  const payload: StepPayload = {
    type: form.type,
    max_score: form.type === "theory" ? 0 : form.maxScore,
    content: {},
    answer_key: {},
    settings,
  };
  if (form.type === "theory") payload.content = { body };
  if (form.type === "single_choice" || form.type === "multiple_choice") {
    payload.content = {
      question: body,
      options: form.options.map(({ id, text }) => ({ id, text: text.trim() })),
    };
    const correct = form.options.filter((option) => option.correct).map((option) => option.id);
    payload.answer_key = { correct: form.type === "single_choice" ? correct[0] : correct };
    if (form.type === "multiple_choice") settings.scoring = form.scoring;
  }
  if (form.type === "free_text") {
    payload.content = {
      question: body,
      require_text: form.requireText,
      min_files: form.minFiles,
      max_files: form.maxFiles,
      allowed_mime: form.allowedMime
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };
    payload.answer_key = {
      reference:
        form.originalReference && docToText(form.originalReference) === form.reference
          ? form.originalReference
          : form.reference.trim()
            ? reuseDocument(form.reference, null)
            : null,
      criteria: form.criteria.trim() || null,
      files: form.referenceFiles,
    };
  }
  if (form.type === "programming") {
    payload.content = {
      statement: body,
      languages: form.languages,
      time_limit_ms: form.timeLimitMs,
      memory_limit_mb: form.memoryLimitMb,
      template: form.template,
      samples: form.samples,
    };
    payload.answer_key = {
      // A curator-only check runs no tests; the hidden form section must not
      // send (possibly unfinished) tests the author cannot see any more.
      test_groups: form.grading === "manual" ? [] : form.testGroups,
      reference_solution: form.referenceSolution || null,
    };
    settings.scoring = form.scoring;
  }
  return payload;
}
