import assert from "node:assert/strict";
import test from "node:test";
import { viewNotification } from "../src/modules/notifications/presentation";
import type { Notification } from "../src/modules/notifications/api";
import { buildAnswer } from "../src/modules/student/steps/answer";
import {
  daysText,
  documentTitle,
  pointsText,
  ratingGoalText,
  ratingPlaceText,
  stepDocument,
  streakText,
} from "../src/modules/student/courses/presentation";
import type { MyRating } from "../src/modules/student/courses/types";
import { renderRichText, richTextImageIds } from "../src/modules/student/courses/rich-text";
import {
  failedTests,
  groupStatus,
  resultStatus,
  verdictLabel,
} from "../src/modules/student/steps/result-presentation";

test("a removed group deadline is shown as a cancelled deadline notification", () => {
  const notification = {
    id: 1,
    type: "deadline_changed",
    severity: "info",
    payload: { course_id: 7, course_title: "Scratch", step_id: null, deadline: null },
    read_at: null,
    created_at: "2026-09-26T12:00:00Z",
  } satisfies Notification;
  const view = viewNotification(notification, "student");
  assert.equal(view.title, "Дедлайн снят");
  assert.equal(view.description, "Срок по «Scratch» снят.");
});

test("student answers use the API shape for each step type", () => {
  const draft = {
    selected: ["first", "second"],
    text: "Ответ",
    files: [7],
    code: "print(1)\n",
    language: "python3" as const,
  };
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
  assert.deepEqual(
    buildAnswer("programming", {}, { ...draft, code: "int main() {}", language: "cpp" }),
    {
      code: "int main() {}",
      language: "cpp",
    },
  );
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

test("programming results show the judge verdict instead of a generic wrong status", () => {
  const details = {
    samples: [],
    groups: [
      {
        name: "Основная группа",
        passed: false,
        tests: [{ verdict: "runtime_error", input: "secret", output: "secret" }],
      },
    ],
  };
  assert.equal(resultStatus("wrong", details), "Ошибка выполнения");
  assert.equal(groupStatus(details.groups[0]!), "ошибка выполнения");
  assert.deepEqual(failedTests(details.groups[0]!), [{ number: 1, verdict: "ошибка выполнения" }]);
  assert.equal(resultStatus("partial", details), "Частично верно");
  assert.equal(verdictLabel("time_limit"), "превышено время");
  assert.equal(verdictLabel("compilation_error"), "ошибка компиляции");
  assert.equal(verdictLabel("wrong_answer"), "неверный ответ");
});

function myRating(overrides: Partial<MyRating> = {}): MyRating {
  return {
    total: 12,
    courses: [{ course_id: 1, title: "Python", points: 8 }],
    streak: { days: 2, bonus: 4, active_today: true },
    group_size: 4,
    place: 2,
    tied_with: 0,
    next_place: { place: 1, points: 14, gap: 2, plan: [5], reachable: true },
    first_place: { place: 1, points: 14, gap: 2, plan: [5], reachable: true },
    opportunities: [],
    ...overrides,
  };
}

test("rating texts: place, goal and streak", () => {
  assert.equal(pointsText(2.5), "2.5 балла");
  assert.equal(daysText(1), "1 день");
  assert.equal(daysText(3), "3 дня");
  assert.equal(daysText(12), "12 дней");

  const rating = myRating();
  assert.equal(ratingPlaceText(rating), "2 место из 4");
  assert.equal(ratingGoalText(rating), "Наберите больше 2 баллов, чтобы подняться на 1 место");
  const blocked = myRating({
    next_place: { place: 1, points: 14, gap: 2, plan: [], reachable: false },
  });
  assert.match(ratingGoalText(blocked) ?? "", /^До 1 места 2 балла: /);
  const gap = (value: number) =>
    ratingGoalText(
      myRating({ next_place: { place: 1, points: 9, gap: value, plan: [], reachable: true } }),
    );
  assert.match(gap(21) ?? "", /больше 21 балла,/);
  assert.match(gap(1.5) ?? "", /больше 1.5 балла,/);
  assert.match(gap(11) ?? "", /больше 11 баллов,/);
  assert.equal(
    ratingGoalText(myRating({ place: 1, next_place: null })),
    "Вы на первом месте в группе",
  );
  // Without a group there is no place and no goal.
  const alone = myRating({ group_size: null, place: null, next_place: null });
  assert.equal(ratingPlaceText(alone), null);
  assert.equal(ratingGoalText(alone), null);

  assert.equal(streakText(rating.streak), "Серия 2 дня");
  assert.equal(
    streakText({ days: 2, bonus: 4, active_today: false }),
    "Серия 2 дня — отправьте решение сегодня, чтобы не прервать",
  );
  assert.match(streakText({ days: 0, bonus: 0, active_today: false }), /^Серии нет/);
});
