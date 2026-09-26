import assert from "node:assert/strict";
import test from "node:test";

import { isNavigationItemActive, navigationByRole } from "../src/modules/navigation/items";
import { CURATOR_REVIEWS_ROUTE } from "../src/pages/curator/reviews/constants";
import { CURATOR_ANALYTICS_ROUTE } from "../src/pages/curator/analytics/constants";
import { WORKSPACE_SECTION_PLACEHOLDERS } from "../src/pages/workspace-section/constants";
import { CURATOR_LEARNERS_ROUTE } from "../src/pages/curator/learners/constants";
import { sortLearners, statusCounts } from "../src/modules/curator/learners/presentation";
import type { Learner } from "../src/modules/curator/learners/types";
import {
  activityLabel,
  averageProgress,
  hardestModule,
  lagCounts,
  stepCellStatus,
  stepSummary,
  studentCourseProgress,
  studentName,
} from "../src/modules/curator/analytics/presentation";
import type { ModuleAnalytics, StudentAnalytics } from "../src/modules/curator/analytics/types";
import {
  attemptNumber,
  nextReviewId,
  reviewTaskTitle,
  selectedReviewId,
  stepNumber,
  taskTitle,
  verdictFor,
  waitingLabel,
} from "../src/modules/curator/reviews/presentation";
import {
  checklistScore,
  checklistVerdict,
  reviewChecklist,
} from "../src/modules/curator/reviews/presentation";
import type { ReviewDetail, ReviewListItem } from "../src/modules/curator/reviews/types";
import {
  questionUpdate,
  questionsForFilter,
  selectedQuestionId,
} from "../src/modules/curator/questions/presentation";
import type { StaffQuestion } from "../src/modules/curator/questions/types";

const works = [11, 12, 13].map((id) => ({ id })) as ReviewListItem[];

test("answering a question advances the unanswered queue and keeps it in all questions", () => {
  const first = { id: 1, answer: null, can_answer: true } as StaffQuestion;
  const second = { id: 2, answer: null, can_answer: true } as StaffQuestion;
  const answered = [{ ...first, answer: "Объяснение" }, second];
  assert.equal(selectedQuestionId([first, second], "unanswered", null), 1);
  assert.equal(selectedQuestionId(answered, "unanswered", null), 2);
  assert.deepEqual(
    questionsForFilter(answered, "unanswered").map((item) => item.id),
    [2],
  );
  assert.deepEqual(
    questionsForFilter(answered, "all").map((item) => item.id),
    [1, 2],
  );
});

test("question answer changes preserve group visibility unless the curator changes it", () => {
  const question = {
    answer: "Сначала посчитай координату",
    visibility: "group",
  } as StaffQuestion;
  assert.deepEqual(questionUpdate(question, "Сначала посчитай координату", "group"), {});
  assert.deepEqual(questionUpdate(question, " Новый ответ ", "group"), {
    answer: "Новый ответ",
  });
  assert.deepEqual(questionUpdate(question, "Сначала посчитай координату", "course"), {
    visibility: "course",
  });
  assert.deepEqual(
    questionUpdate({ ...question, answer: null, visibility: "private" }, " Новый ответ ", "course"),
    { answer: "Новый ответ", visibility: "course" },
  );
  assert.deepEqual(
    questionUpdate({ ...question, visibility: "course" }, "Сначала посчитай координату", "private"),
    { visibility: "private" },
  );
});

test("curator review queue is the first navigation item and stays active on a work", () => {
  const first = navigationByRole.curator[0];
  assert.equal(first?.path, CURATOR_REVIEWS_ROUTE.path);
  assert.equal(first?.label, "Работы на проверку");
  assert.equal(isNavigationItemActive(first!, "/curator/reviews/4/12"), true);
});

test("curator analytics is available in navigation and derives group totals from API rows", () => {
  assert.ok(navigationByRole.curator.some((item) => item.path === CURATOR_ANALYTICS_ROUTE.path));
  assert.equal(
    WORKSPACE_SECTION_PLACEHOLDERS.some((item) => item.path === CURATOR_ANALYTICS_ROUTE.path),
    false,
  );
  const rows = [
    {
      surname: "Иванов",
      name: "Иван",
      patronymic: "",
      username: "ivan",
      modules: [{ module_id: 1, steps_completed: 1, steps_total: 4 }],
      lag: { status: "falling_behind" },
    },
    {
      surname: "",
      name: "",
      patronymic: "",
      username: "masha",
      modules: [{ module_id: 1, steps_completed: 3, steps_total: 4 }],
      lag: { status: "slowed" },
    },
    {
      surname: "",
      name: "",
      patronymic: "",
      username: "petr",
      modules: [{ module_id: 1, steps_completed: 2, steps_total: 4 }],
      lag: { status: "on_track" },
    },
  ] as StudentAnalytics[];
  assert.equal(averageProgress(rows), 50);
  assert.deepEqual(lagCounts(rows), { falling: 1, slowed: 1, onTrack: 1 });
  assert.equal(averageProgress([]), null);
  assert.deepEqual(studentCourseProgress(rows[0]!), { completed: 1, total: 4, percent: 25 });
  assert.equal(studentName(rows[0]!), "Иванов Иван");
  assert.equal(studentName(rows[1]!), "masha");
  const modules = [
    { module_id: 1, first_attempt_percent: 70 },
    { module_id: 2, first_attempt_percent: 41 },
    { module_id: 3, first_attempt_percent: null },
  ] as Parameters<typeof hardestModule>[0];
  assert.equal(hardestModule(modules)?.module_id, 2);
  assert.equal(hardestModule([modules[2]!]), null);
});

test("module analytics uses step cells for attempt and review summaries", () => {
  const cell = (overrides: Record<string, unknown>) => ({
    step_id: 10,
    state: "not_started",
    earned: 0,
    max_score: 1,
    completed: false,
    attempts: 0,
    first_attempt_solved: null,
    has_unresolved_return: false,
    last_submission_at: null,
    ...overrides,
  });
  const data = {
    students: [
      {
        steps: [
          cell({ state: "passed", completed: true, attempts: 1, first_attempt_solved: true }),
        ],
      },
      { steps: [cell({ state: "failed", attempts: 2, has_unresolved_return: true })] },
      { steps: [cell({ state: "checking", attempts: 4 })] },
      { steps: [cell({ state: "attempts_exhausted", attempts: 3 })] },
      { steps: [cell({})] },
    ],
  } as ModuleAnalytics;
  assert.deepEqual(stepSummary(data, 10), {
    total: 5,
    submitted: 4,
    firstAttempt: 1,
    completed: 1,
    attempts: [1, 1, 1, 1],
    returned: 1,
    failed: 1,
    checking: 1,
  });
  assert.deepEqual(stepCellStatus(data.students[1]!.steps[0]), { text: "↺", tone: "return" });
  assert.deepEqual(stepCellStatus(data.students[4]!.steps[0]), { text: "–", tone: "idle" });
  assert.equal(activityLabel(null), "не отправлял");
  assert.equal(
    activityLabel(new Date(2026, 8, 25, 23).toISOString(), new Date(2026, 8, 26, 12)),
    "вчера",
  );
});

test("check all opens the first work; a specific link opens its work", () => {
  assert.equal(selectedReviewId(works, null), 11);
  assert.equal(selectedReviewId(works, 13), 13);
  assert.equal(selectedReviewId(works, 999), 11);
});

test("saving advances to the next pending work or returns to courses", () => {
  assert.equal(nextReviewId(works, 11), 12);
  assert.equal(nextReviewId(works, 12), 13);
  assert.equal(nextReviewId(works, 13), 12);
  assert.equal(nextReviewId([works[0]!], 11), null);
});

test("all three grading choices use the review API contract", () => {
  assert.deepEqual(verdictFor("full", 2, 8, " Отлично "), {
    verdict: "accepted",
    score: 8,
    comment: "Отлично",
  });
  assert.deepEqual(verdictFor("partial", 5, 8, ""), {
    verdict: "accepted",
    score: 5,
    comment: null,
  });
  assert.deepEqual(verdictFor("revise", 5, 8, "Исправь угол"), {
    verdict: "rejected",
    score: 0,
    comment: "Исправь угол",
  });
});

test("title is read from the marked heading in the answered revision", () => {
  const content = {
    question: {
      type: "doc",
      content: [
        {
          type: "heading",
          attrs: { level: 1, zebra_title: true },
          content: [{ type: "text", text: "Первый проект" }],
        },
        { type: "paragraph", content: [{ type: "text", text: "Описание" }] },
      ],
    },
  };
  assert.equal(taskTitle(content, 42), "Первый проект");
  assert.equal(taskTitle({ question: { type: "doc", content: [] } }, 42), "Задание #42");
});

test("queue uses title and number supplied by the review API", () => {
  const work = {
    id: 12,
    step_id: 42,
    task_title: "Кот по кругу",
    task_number: "1.2.4",
  } as ReviewListItem;
  assert.equal(reviewTaskTitle(work), "Кот по кругу");
  assert.equal(stepNumber(work), "1.2.4");
  assert.equal(reviewTaskTitle({ ...work, task_title: "" }), "Задание #42");
  assert.equal(stepNumber({ ...work, task_number: "" }), "#42");
});

test("attempts_before becomes a one-based attempt number", () => {
  assert.equal(attemptNumber({ attempts_before: 0 } as ReviewListItem), 1);
  assert.equal(attemptNumber({ attempts_before: 2 } as ReviewListItem), 3);
});

test("waiting time uses minutes and hours from the API", () => {
  assert.equal(waitingLabel(0), "меньше минуты");
  assert.equal(waitingLabel(2 * 3600 + 40 * 60), "2 ч 40 мин");
  assert.equal(waitingLabel(27 * 3600), "1 д 3 ч");
});

test("learners: the page is real and needy students come first", () => {
  assert.ok(navigationByRole.curator.some((item) => item.path === CURATOR_LEARNERS_ROUTE.path));
  assert.equal(
    WORKSPACE_SECTION_PLACEHOLDERS.some((item) => item.path === CURATOR_LEARNERS_ROUTE.path),
    false,
  );
  const learner = (surname: string, status: Learner["status"]): Learner => ({
    student_id: surname.length,
    username: surname.toLowerCase(),
    name: "Имя",
    surname,
    patronymic: "",
    status,
    courses: [],
  });
  const students = [
    learner("Яковлев", "on_track"),
    learner("Борисов", null),
    learner("Петров", "slowed"),
    learner("Антонов", "on_track"),
    learner("Иванов", "falling_behind"),
  ];
  assert.deepEqual(
    sortLearners(students).map((s) => s.surname),
    ["Иванов", "Петров", "Антонов", "Яковлев", "Борисов"],
  );
  assert.deepEqual(statusCounts(students), { falling_behind: 1, slowed: 1, on_track: 2 });
});

test("checklist review: the score is the points of met criteria", () => {
  const items = [
    { id: "plan", text: "План", points: 2, hint: "3 шага" },
    { id: "works", text: "Работает", points: 3.5, hint: null },
  ];
  const detail = { settings: { checklist: items } } as unknown as ReviewDetail;
  assert.deepEqual(reviewChecklist(detail), items);
  assert.deepEqual(reviewChecklist({ settings: {} } as unknown as ReviewDetail), []);
  assert.equal(checklistScore(items, []), 0);
  assert.equal(checklistScore(items, ["works"]), 3.5);
  assert.equal(checklistScore(items, ["plan", "works", "unknown"]), 5.5);
  // No score is sent: the server counts it from the criteria.
  assert.deepEqual(checklistVerdict(false, ["plan"], "  "), {
    verdict: "rejected",
    checked: ["plan"],
    comment: null,
  });
});
