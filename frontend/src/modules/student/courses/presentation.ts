import { pluralRu, stepsText } from "@/modules/shared/plural";
import type { RichDocument, RichNode, StepType } from "./types";

export const stepLabels: Record<StepType, string> = {
  theory: "Теория",
  single_choice: "Вопрос с одним ответом",
  multiple_choice: "Вопрос с несколькими ответами",
  free_text: "Задание с произвольным ответом",
  programming: "Задача с кодом",
  number: "Вопрос с ответом в виде числа",
  short_text: "Вопрос с коротким ответом",
};

/** Russian noun agreement: 1 балл, 2 балла, 5 баллов, 11 баллов, 21 балл. */
export function pointsWord(count: number): string {
  // Fractional points (partial scores) read as "2,5 балла".
  if (!Number.isInteger(count)) return "балла";
  return pluralRu(count, "балл", "балла", "баллов");
}

export function pointsText(count: number): string {
  return `${count} ${pointsWord(count)}`;
}

export function daysText(count: number): string {
  return `${count} ${pluralRu(count, "день", "дня", "дней")}`;
}

type Rating = import("./types").MyRating;
type StreakInfo = import("./types").Streak;

/** "3-е место в группе из 8"; null without a group. */
export function ratingPlaceText(rating: Rating): string | null {
  if (rating.place == null || rating.group_size == null) return null;
  return `${rating.place}-е место в группе из ${rating.group_size}`;
}

// How a single step of each kind is named in "Это одна задача с тестами".
const ONE_STEP: Record<string, string> = {
  programming: "одна задача с тестами",
  single_choice: "один контрольный вопрос",
  multiple_choice: "один контрольный вопрос",
  free_text: "одно задание с ответом",
  number: "один вопрос с числовым ответом",
  short_text: "один вопрос с коротким ответом",
};

/** What it takes to reach the next place, with the points to highlight:
 * "До 2-го места" + "9 баллов" + ". Это одна задача с тестами." Equal
 * ratings share a place, so the gap reaches it; the plan is enough to
 * overtake. Null without a group. */
export function ratingGoal(
  rating: Rating,
): { before: string; points: string; after: string } | null {
  if (rating.place == null) return null;
  const target = rating.next_place;
  if (!target || target.gap == null)
    return { before: "Вы на первом месте в группе", points: "", after: "" };
  const plan = rating.opportunities.filter((o) => target.plan.includes(o.step_id));
  let after = ". Заданий пока не хватает — помогут дни серии.";
  if (target.reachable && plan.length === 1)
    after = `. Это ${ONE_STEP[plan[0]!.type] ?? "один шаг"}.`;
  else if (target.reachable) after = `. Это ${stepsText(plan.length)}.`;
  return { before: `До ${target.place}-го места`, points: pointsText(target.gap), after };
}

export function streakHint(streak: StreakInfo): string {
  if (streak.active_today) return "Сегодня уже засчитано — завтра серия продолжится.";
  if (streak.days) return "Сдай один шаг сегодня — серия продолжится.";
  return "Сдай один шаг сегодня — начнётся серия.";
}

export type StreakCellState = "done" | "today" | "missed" | "future";

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

/** The week of the streak: days with counted work, today still open,
 * missed and future days. */
export function streakWeek(streak: StreakInfo): { label: string; state: StreakCellState }[] {
  return streak.week.map((day, index) => ({
    label: WEEKDAYS[index] ?? "",
    state: day.active
      ? "done"
      : day.date === streak.today
        ? "today"
        : day.date > streak.today
          ? "future"
          : "missed",
  }));
}

export function progressText(completed: number, total: number): string {
  return total ? `${completed} из ${total} шагов` : "Шагов пока нет";
}

export function stepDocument(
  type: StepType,
  content: Record<string, unknown>,
): RichDocument | null {
  const key = type === "theory" ? "body" : type === "programming" ? "statement" : "question";
  const value = content[key];
  return value && typeof value === "object" && (value as RichDocument).type === "doc"
    ? (value as RichDocument)
    : null;
}

function nodeText(node: RichNode): string {
  return node.type === "text" ? (node.text ?? "") : (node.content ?? []).map(nodeText).join(" ");
}

export function documentTitle(doc: RichDocument | null, fallback: string): string {
  if (!doc) return fallback;
  const heading = doc.content?.find((node) => node.type === "heading");
  const first = heading ?? doc.content?.find((node) => nodeText(node).trim());
  return first ? nodeText(first).replace(/\s+/g, " ").trim().slice(0, 100) || fallback : fallback;
}

export function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })
      .response;
    if (response?.status === 404) return "Курс или шаг не найден.";
    if (response?.status === 403) return "Этот материал пока недоступен.";
    if (typeof response?.data?.detail === "string") return response.data.detail;
  }
  return "Не удалось загрузить данные. Попробуйте ещё раз.";
}

export function submissionLabel(status: string): string {
  switch (status) {
    case "queued":
      return "Ожидает проверки";
    case "running":
      return "Проверяется";
    case "pending_review":
      return "На проверке у куратора";
    case "correct":
    case "accepted":
      return "Зачтено";
    case "partial":
      return "Частично верно";
    case "wrong":
    case "rejected":
      return "Пока не то";
    case "error":
      return "Ошибка проверки";
    default:
      return status;
  }
}

export function blockReason(reason: string | null): string {
  switch (reason) {
    case "The previous submission is still being checked":
      return "Предыдущее решение ещё проверяется.";
    case "The step is already solved with the maximum score":
      return "Шаг уже выполнен на максимальный балл.";
    case "No attempts left":
      return "Попытки закончились.";
    default:
      return reason ?? "";
  }
}

export function notificationPresentation(notification: import("./types").StudentNotification): {
  title: string;
  description: string;
  tone: "success" | "warning" | "info" | "neutral";
} {
  const payload = notification.payload;
  const courseTitle = typeof payload.course_title === "string" ? payload.course_title : null;
  const stepTitle = typeof payload.step_title === "string" ? payload.step_title : null;
  const objectTitle = stepTitle ?? courseTitle;

  switch (notification.type) {
    case "submission_reviewed":
      return {
        title: "Работа проверена",
        description: objectTitle
          ? `«${objectTitle}» — появился результат проверки.`
          : "Появился результат проверки вашей работы.",
        tone: notification.severity === "warning" ? "warning" : "success",
      };
    case "step_solved":
      return {
        title: "Шаг зачтён",
        description: objectTitle
          ? `«${objectTitle}» успешно завершён.`
          : "Один из шагов курса успешно завершён.",
        tone: "success",
      };
    case "step_unlocked":
      return {
        title: "Открыт новый шаг",
        description: objectTitle
          ? `Теперь доступен «${objectTitle}».`
          : "В курсе стал доступен следующий шаг.",
        tone: "info",
      };
    case "deadline_approaching":
      return {
        title: "Скоро дедлайн",
        description: objectTitle
          ? `Проверьте срок для «${objectTitle}».`
          : "У одного из заданий скоро заканчивается срок.",
        tone: "warning",
      };
    case "deadline_passed":
      return {
        title: "Дедлайн прошёл",
        description: objectTitle
          ? `Срок для «${objectTitle}» уже прошёл.`
          : "У одного из заданий истёк срок.",
        tone: "warning",
      };
    case "course_completed":
      return {
        title: "Курс завершён",
        description: courseTitle
          ? `Курс «${courseTitle}» пройден.`
          : "Поздравляем — курс завершён.",
        tone: "success",
      };
    case "course_published":
      return {
        title: "Доступен курс",
        description: courseTitle
          ? `Опубликован курс «${courseTitle}».`
          : "Для вас появился новый опубликованный курс.",
        tone: "info",
      };
    default:
      return {
        title: "Новое событие",
        description: objectTitle
          ? `Есть обновление по «${objectTitle}».`
          : "В вашем обучении появилось обновление.",
        tone: "neutral",
      };
  }
}
