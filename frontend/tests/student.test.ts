import assert from "node:assert/strict";
import test from "node:test";
import { buildAnswer } from "../src/modules/student/steps/answer";
import {
  daysText,
  documentTitle,
  pointsText,
  ratingGoal,
  ratingPlaceText,
  stepDocument,
  streakHint,
  streakWeek,
} from "../src/modules/student/courses/presentation";
import type { MyRating } from "../src/modules/student/courses/types";
import {
  hexLayout,
  initialSkill,
  skillCountsText,
  skillSegments,
  skillSub,
} from "../src/modules/student/skills/presentation";
import type { Skill } from "../src/modules/student/skills/types";
import { renderRichText, richTextImageIds } from "../src/modules/student/courses/rich-text";
import {
  failedTests,
  groupStatus,
  resultStatus,
  verdictLabel,
} from "../src/modules/student/steps/result-presentation";

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
    streak: {
      days: 2,
      bonus: 4,
      active_today: true,
      today: "2026-09-24",
      week: ["21", "22", "23", "24", "25", "26", "27"].map((day) => ({
        date: `2026-09-${day}`,
        active: day === "23" || day === "24",
      })),
    },
    group_size: 8,
    place: 3,
    tied_with: 0,
    next_place: { place: 2, points: 21, gap: 9, plan: [5], reachable: true },
    first_place: { place: 1, points: 30, gap: 18, plan: [5, 6], reachable: true },
    opportunities: [
      {
        course_id: 1,
        course_title: "Python",
        step_id: 5,
        module_id: 1,
        module_title: "Циклы",
        position: 2,
        type: "programming",
        action: "complete",
        can_gain: 10,
      },
      {
        course_id: 1,
        course_title: "Python",
        step_id: 6,
        module_id: 1,
        module_title: "Циклы",
        position: 3,
        type: "single_choice",
        action: "complete",
        can_gain: 10,
      },
    ],
    ...overrides,
  };
}

test("rating widget texts: place, goal and the week of the streak", () => {
  assert.equal(pointsText(2.5), "2.5 балла");
  assert.equal(daysText(1), "1 день");
  assert.equal(daysText(3), "3 дня");
  assert.equal(daysText(12), "12 дней");

  const rating = myRating();
  assert.equal(ratingPlaceText(rating), "3-е место в группе из 8");
  assert.deepEqual(ratingGoal(rating), {
    before: "До 2-го места",
    points: "9 баллов",
    after: ". Это одна задача с тестами.",
  });
  const two = myRating({
    next_place: { place: 2, points: 21, gap: 9, plan: [5, 6], reachable: true },
  });
  assert.equal(ratingGoal(two)?.after, ". Это 2 шага.");
  const blocked = myRating({
    next_place: { place: 2, points: 21, gap: 9, plan: [], reachable: false },
  });
  assert.match(ratingGoal(blocked)?.after ?? "", /не хватает/);
  assert.equal(
    ratingGoal(myRating({ place: 1, next_place: null }))?.before,
    "Вы на первом месте в группе",
  );
  // Without a group there is no place and no goal.
  const alone = myRating({ group_size: null, place: null, next_place: null });
  assert.equal(ratingPlaceText(alone), null);
  assert.equal(ratingGoal(alone), null);

  const week = (today: string, active: string[], days: number) =>
    streakWeek({
      days,
      bonus: 2 * days,
      active_today: active.includes(today),
      today,
      week: ["21", "22", "23", "24", "25", "26", "27"].map((day) => ({
        date: `2026-09-${day}`,
        active: active.includes(`2026-09-${day}`),
      })),
    }).map((day) => `${day.label}:${day.state}`);
  // Every day with counted work is marked, the earlier run too.
  assert.deepEqual(week("2026-09-26", ["2026-09-24", "2026-09-26"], 1), [
    "Пн:missed",
    "Вт:missed",
    "Ср:missed",
    "Чт:done",
    "Пт:missed",
    "Сб:done",
    "Вс:future",
  ]);
  assert.deepEqual(week("2026-09-25", ["2026-09-23", "2026-09-24"], 2).slice(2, 5), [
    "Ср:done",
    "Чт:done",
    "Пт:today",
  ]);
  const open = {
    ...rating.streak,
    active_today: false,
    week: rating.streak.week.map((d) => ({ ...d, active: d.date === "2026-09-23" })),
  };
  assert.equal(streakHint(open), "Сдай один шаг сегодня — серия продолжится.");
  assert.match(streakHint(rating.streak), /уже засчитано/);
  assert.match(streakHint({ ...open, days: 0 }), /начнётся серия/);
});

function skill(overrides: Partial<Skill> = {}): Skill {
  return {
    name: "Циклы",
    module_id: 3,
    module_title: "Повторение",
    state: "in_progress",
    steps_total: 6,
    steps_completed: 2,
    steps_checking: 1,
    steps_returned: 1,
    next_step_id: 9,
    current: false,
    opens_after: null,
    ...overrides,
  };
}

test("skill map: courses are bands of honeycomb cells", () => {
  const layout = hexLayout([
    { course_id: 1, title: "Scratch", skills: Array.from({ length: 5 }, () => skill()) },
    { course_id: 2, title: "Python", skills: [skill({ current: true })] },
  ]);
  // Four cells per column: Scratch takes two columns, Python one, then
  // one "new course" cell.
  assert.deepEqual(
    layout.cells.map((cell) => [cell.courseId, cell.x, cell.y]),
    [
      [1, 40, 48],
      [1, 40, 162],
      [1, 40, 276],
      [1, 40, 390],
      [1, 138, 105], // odd column: half a cell lower
      [2, 236, 48],
      [0, 334, 219],
    ],
  );
  assert.deepEqual(
    layout.labels.map((label) => [label.text, label.x]),
    [
      ["SCRATCH", 40],
      ["PYTHON", 236],
      ["ПОЯВИТСЯ ПОЗЖЕ", 334],
    ],
  );
  assert.equal(layout.cells.at(-1)!.skill, null);
  assert.deepEqual(
    initialSkill([{ course_id: 2, title: "Python", skills: [skill(), skill({ current: true })] }]),
    { courseId: 2, index: 1 },
  );
});

test("skill map: what a cell and the selected card say", () => {
  assert.equal(skillSub(skill()), "2 из 6 · ↺ 1");
  assert.equal(skillSub(skill({ steps_returned: 0 })), "2 из 6");
  assert.equal(skillSub(skill({ state: "locked", opens_after: "Основы" })), "после «Основы»");
  assert.equal(
    skillSub(skill({ steps_total: 0, steps_completed: 0, steps_checking: 0, steps_returned: 0 })),
    "шагов пока нет",
  );
  assert.deepEqual(skillSegments(skill()), [
    "completed",
    "completed",
    "checking",
    "returned",
    "ahead",
    "ahead",
  ]);
  assert.equal(skillCountsText(skill()), "2 зачтено · 1 на проверке · 1 возвращено · 2 впереди");
  assert.equal(
    skillCountsText(skill({ steps_checking: 0, steps_returned: 0 })),
    "2 зачтено · 4 впереди",
  );
});
