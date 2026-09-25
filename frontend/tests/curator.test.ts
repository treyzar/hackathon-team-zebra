import assert from "node:assert/strict";
import test from "node:test";

import { isNavigationItemActive, navigationByRole } from "../src/modules/navigation/items";
import { CURATOR_REVIEWS_ROUTE } from "../src/pages/curator/reviews/constants";
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
import type { ReviewListItem } from "../src/modules/curator/reviews/types";
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
