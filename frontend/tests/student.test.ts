import assert from "node:assert/strict";
import test from "node:test";
import { buildAnswer } from "../src/modules/student/steps/answer";
import {
  documentTitle,
  pointsText,
  stepDocument,
} from "../src/modules/student/courses/presentation";
import { renderRichText, richTextImageIds } from "../src/modules/student/courses/rich-text";

test("student answers use the API shape for each step type", () => {
  const draft = { selected: ["first", "second"], text: "Ответ", files: [7], code: "print(1)\n" };
  assert.deepEqual(buildAnswer("theory", {}, draft), {});
  assert.deepEqual(buildAnswer("single_choice", {}, draft), { option_id: "first" });
  assert.deepEqual(buildAnswer("multiple_choice", {}, draft), { option_ids: ["first", "second"] });
  assert.deepEqual(buildAnswer("free_text", { require_text: true, min_files: 1 }, draft), {
    text: "Ответ",
    files: [7],
  });
  assert.deepEqual(buildAnswer("programming", {}, draft), {
    code: "print(1)\n",
    language: "python3",
  });
  assert.equal(buildAnswer("programming", {}, { ...draft, code: "  " }), null);
  assert.equal(
    buildAnswer("free_text", { require_text: true, min_files: 1 }, { ...draft, files: [] }),
    null,
  );
});

test("course step title comes from the public content document", () => {
  const content = {
    statement: {
      type: "doc",
      content: [{ type: "heading", content: [{ type: "text", text: "Сложите числа" }] }],
    },
  };
  assert.equal(documentTitle(stepDocument("programming", content), "Задача"), "Сложите числа");
  assert.equal(stepDocument("programming", { answer_key: { secret: true } }), null);
});

test("rich text escapes authored text and rejects unsafe links and image URLs", () => {
  const document = {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [
          {
            type: "text",
            text: '<script>alert("x")</script>',
            marks: [{ type: "link", attrs: { href: "javascript:alert(1)" } }],
          },
        ],
      },
      { type: "paragraph", content: [{ type: "image", attrs: { file_id: 11 } }] },
    ],
  };
  assert.deepEqual(richTextImageIds(document), [11]);
  const output = renderRichText(document, new Map([[11, "javascript:alert(1)"]]));
  assert.match(output, /&lt;script&gt;/);
  assert.doesNotMatch(output, /<script|href=|<img/);
  assert.match(
    renderRichText(document, new Map([[11, "https://files.example.org/a.png"]])),
    /<img src="https:\/\/files.example.org\/a.png"/,
  );
});

test("points agree with the number in Russian", () => {
  assert.equal(pointsText(1), "1 балл");
  assert.equal(pointsText(2), "2 балла");
  assert.equal(pointsText(5), "5 баллов");
  assert.equal(pointsText(11), "11 баллов");
  assert.equal(pointsText(14), "14 баллов");
  assert.equal(pointsText(21), "21 балл");
  assert.equal(pointsText(0), "0 баллов");
});
