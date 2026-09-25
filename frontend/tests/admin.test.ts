import assert from "node:assert/strict";
import { test } from "node:test";
import {
  formFromStep,
  newStepForm,
  payloadFromForm,
  validateStepForm,
} from "../src/modules/admin/steps/editor-model";
import { textToDoc } from "../src/modules/admin/shared/format";
import {
  docImageIds,
  docToQuillOps,
  imageUrl,
  quillOpsToDoc,
} from "../src/modules/admin/steps/quill-document";
import type { Step } from "../src/modules/admin/shared/types";
import { parseMethodText } from "../src/modules/admin/courses/method-parser";
import { reorderIds } from "../src/modules/admin/courses/reorder";

test("dragging a step changes only its position within its module", () => {
  assert.deepEqual(reorderIds([10, 20, 30, 40], 10, 30, true), [20, 30, 10, 40]);
  assert.deepEqual(reorderIds([10, 20, 30, 40], 40, 20, false), [10, 40, 20, 30]);
  assert.deepEqual(reorderIds([10, 20, 30], 20, 20, true), [10, 20, 30]);
  assert.deepEqual(reorderIds([10, 20, 30], 20, 90, false), [10, 20, 30]);
});

test("Quill text, formatting, lists and uploaded images survive a document round trip", () => {
  const source = imageUrl("https://storage.example/image.png?signature=abc", 42);
  const document = quillOpsToDoc([
    { insert: "Заголовок" },
    { insert: "\n", attributes: { header: 1 } },
    { insert: "Жирный", attributes: { bold: true } },
    { insert: "\n", attributes: { list: "bullet" } },
    { insert: { image: source } },
    { insert: "\n" },
  ]);
  assert.equal(document.content[0]?.type, "heading");
  assert.equal(document.content[1]?.type, "bulletList");
  assert.deepEqual(docImageIds(document), [42]);
  assert.deepEqual(docToQuillOps(document, new Map([[42, "https://storage.example/new.png"]])), [
    { insert: "Заголовок" },
    { insert: "\n", attributes: { header: 1 } },
    { insert: "Жирный", attributes: { bold: true } },
    { insert: "\n", attributes: { list: "bullet" } },
    { insert: { image: imageUrl("https://storage.example/new.png", 42) } },
    { insert: "\n" },
  ]);
});

test("external image URLs cannot be saved as course content", () => {
  assert.throws(
    () => quillOpsToDoc([{ insert: { image: "https://example.com/photo.png" } }, { insert: "\n" }]),
    /загрузки/,
  );
});

test("saving a free text revision retains reference files and MIME restrictions", () => {
  const step: Step = {
    id: 7,
    module_id: 2,
    type: "free_text",
    position: 1,
    is_hidden: false,
    revision: {
      number: 3,
      created_at: "2026-09-25T12:00:00Z",
      author_id: 1,
      comment: null,
      is_breaking: false,
      max_score: 5,
      schema_version: 1,
      content: {
        question: textToDoc("Опишите решение"),
        require_text: true,
        min_files: 1,
        max_files: 2,
        allowed_mime: ["image/png"],
      },
      answer_key: { reference: textToDoc("Пример"), criteria: "Проверить объяснение", files: [17] },
      settings: { grading: "manual", max_attempts: 2, show_answer: "never" },
    },
  };
  const form = formFromStep(step);
  assert.equal(validateStepForm(form), null);
  const payload = payloadFromForm(form);
  assert.deepEqual(payload.answer_key.files, [17]);
  assert.deepEqual(payload.content.allowed_mime, ["image/png"]);
  assert.deepEqual(payload.answer_key.reference, textToDoc("Пример"));
});

test("choice and programming rules catch invalid drafts before a request", () => {
  const choice = newStepForm("single_choice");
  choice.body = textToDoc("Вопрос");
  choice.options[0]!.text = "А";
  choice.options[1]!.text = "Б";
  assert.equal(validateStepForm(choice), null);
  choice.options[1]!.correct = true;
  assert.match(validateStepForm(choice) ?? "", /ровно один/);

  const code = newStepForm("programming");
  code.body = textToDoc("Напишите программу");
  code.scoring = "per_group";
  code.maxScore = 5;
  assert.match(validateStepForm(code) ?? "", /Сумма баллов/);
});

test("editing a programming step keeps file-backed hidden tests", () => {
  const step: Step = {
    id: 12,
    module_id: 3,
    type: "programming",
    position: 2,
    is_hidden: false,
    revision: {
      number: 2,
      created_at: "2026-09-25T12:00:00Z",
      author_id: 1,
      comment: null,
      is_breaking: false,
      max_score: 10,
      schema_version: 1,
      content: {
        statement: textToDoc("Сложите числа"),
        language: "python3",
        samples: [],
        time_limit_ms: 2000,
        memory_limit_mb: 256,
        template: "",
      },
      answer_key: {
        test_groups: [
          {
            name: "Длинный тест",
            points: 10,
            tests: [{ input: "", output: "", input_file: 101, output_file: 102 }],
          },
        ],
        reference_solution: null,
      },
      settings: {
        grading: "tests",
        scoring: "all_or_nothing",
        max_attempts: null,
        show_answer: "never",
      },
    },
  };
  const form = formFromStep(step);
  assert.equal(validateStepForm(form), null);
  assert.deepEqual(payloadFromForm(form).answer_key.test_groups, [
    {
      name: "Длинный тест",
      points: 10,
      tests: [{ input: "", output: "", input_file: 101, output_file: 102 }],
    },
  ]);
});

test("a step title is saved as a marked heading and restored without duplicating it in the editor", () => {
  const form = newStepForm("theory");
  form.title = "Повторить и всегда";
  form.body = textToDoc("Цикл повторяет действия.");
  const payload = payloadFromForm(form);
  const body = payload.content.body as { content: Record<string, unknown>[] };
  assert.deepEqual(body.content[0]?.attrs, { level: 1, zebra_title: true });
  const step: Step = {
    id: 9,
    module_id: 1,
    type: "theory",
    position: 0,
    is_hidden: false,
    revision: {
      number: 1,
      created_at: "2026-09-25T12:00:00Z",
      author_id: 1,
      comment: null,
      is_breaking: false,
      max_score: 0,
      schema_version: 1,
      content: payload.content,
      answer_key: {},
      settings: { grading: "none", show_answer: "never" },
    },
  };
  const restored = formFromStep(step);
  assert.equal(restored.title, form.title);
  assert.deepEqual(restored.body, form.body);
});

test("method preview identifies step boundaries and unsupported step types", () => {
  const parsed = parseMethodText(
    "Модуль 1.3. Условия\nШаг 1.3.2. Проверь себя\nТип шага Контрольный вопрос\nПроверка Автоматическая\nШаг 1.3.3. Робот\nТип шага Робототехника",
  );
  assert.equal(parsed.modules, 1);
  assert.deepEqual(parsed.steps.map((step) => [step.number, step.supported]), [
    ["1.3.2", true],
    ["1.3.3", false],
  ]);
});
