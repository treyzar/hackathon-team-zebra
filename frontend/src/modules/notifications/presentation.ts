import type { Notification, NotificationSeverity } from "./api";
import type { UserRole } from "@/api/http";
import { STUDENT_COURSE_ROUTE } from "@/pages/student/course/constants";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";

export interface NotificationView {
  title: string;
  description: string;
  tone: NotificationSeverity;
  to: { name: string; params: Record<string, number> } | { name: string } | null;
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function str(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

export function viewNotification(n: Notification, role: UserRole | null): NotificationView {
  const payload = n.payload;
  const courseId = num(payload.course_id);
  const stepId = num(payload.step_id);
  const courseTitle = str(payload.course_title);
  const objectTitle = str(payload.step_title) ?? courseTitle;
  const tone = n.severity;

  const stepTarget =
    role === "student" && courseId && stepId
      ? { name: STUDENT_STEP_ROUTE.name, params: { courseId, stepId } }
      : null;
  const courseTarget =
    role === "student" && courseId
      ? { name: STUDENT_COURSE_ROUTE.name, params: { courseId } }
      : null;

  switch (n.type) {
    case "submission_reviewed":
      return {
        title: "Работа проверена",
        description: objectTitle
          ? `«${objectTitle}» — появился результат проверки.`
          : "Появился результат проверки вашей работы.",
        tone,
        to: stepTarget,
      };
    case "submission_pending_review":
      return {
        title: "Новое решение",
        description: objectTitle
          ? `Ученик отправил решение по «${objectTitle}».`
          : "Ученик отправил решение на проверку.",
        tone,
        to: null,
      };
    case "submission_queue_reminder": {
      const pending = num(payload.pending) ?? 0;
      return {
        title: "Очередь проверки",
        description: `Ждут проверки: ${pending}.`,
        tone,
        to: null,
      };
    }
    case "step_solved":
      return {
        title: "Шаг зачтён",
        description: objectTitle ? `«${objectTitle}» зачтён.` : "Шаг курса зачтён.",
        tone,
        to: stepTarget ?? courseTarget,
      };
    case "step_unlocked":
      return {
        title: "Открыт новый шаг",
        description: objectTitle
          ? `Теперь доступен «${objectTitle}».`
          : "В курсе открылся следующий шаг.",
        tone,
        to: stepTarget ?? courseTarget,
      };
    case "step_breaking_change": {
      const outdated = num(payload.outdated) ?? 0;
      return {
        title: "Шаг обновлён",
        description: objectTitle
          ? `«${objectTitle}» изменён, предыдущие решения (${outdated}) помечены устаревшими.`
          : "Задание изменено, ученику выданы новые попытки.",
        tone,
        to: courseTarget,
      };
    }
    case "deadline_approaching": {
      const hours = num(payload.hours_left);
      return {
        title: "Скоро дедлайн",
        description: objectTitle
          ? `«${objectTitle}»${hours != null ? ` — осталось ${hours} ч.` : ""}`
          : "У задания скоро истекает срок.",
        tone: "warning",
        to: stepTarget ?? courseTarget,
      };
    }
    case "deadline_passed":
      return {
        title: "Дедлайн прошёл",
        description: objectTitle ? `Срок по «${objectTitle}» истёк.` : "Срок задания истёк.",
        tone: "warning",
        to: stepTarget ?? courseTarget,
      };
    case "deadline_changed":
      return {
        title: "Дедлайн изменён",
        description: objectTitle ? `Обновлён срок по «${objectTitle}».` : "Обновлён срок задания.",
        tone: "info",
        to: stepTarget ?? courseTarget,
      };
    case "question_asked":
      return {
        title: "Новый вопрос по шагу",
        description: "Ученик задал вопрос.",
        tone,
        to: null,
      };
    case "question_answered":
      return {
        title: "Ответ на вопрос",
        description: objectTitle ? `По «${objectTitle}» появился ответ.` : "Появился ответ на ваш вопрос.",
        tone,
        to: stepTarget ?? courseTarget,
      };
    case "course_completed":
      return {
        title: "Курс завершён",
        description: courseTitle ? `Курс «${courseTitle}» пройден.` : "Курс завершён.",
        tone: "success",
        to: courseTarget,
      };
    case "course_published":
      return {
        title: "Курс опубликован",
        description: courseTitle ? `Опубликован «${courseTitle}».` : "Появился новый курс.",
        tone: "info",
        to: courseTarget,
      };
    case "course_attention_needed":
      return {
        title: "Курс требует внимания",
        description: courseTitle ? `«${courseTitle}» — есть вопросы от учеников.` : "Проверьте курс.",
        tone,
        to: null,
      };
    case "added_to_group": {
      const name = str(payload.group_name);
      return {
        title: "Вы в группе",
        description: name ? `Добавлены в группу «${name}».` : "Добавлены в группу.",
        tone,
        to: null,
      };
    }
    case "moved_to_group": {
      const name = str(payload.group_name);
      return {
        title: "Перевод в группу",
        description: name ? `Переведены в группу «${name}».` : "Вы переведены в другую группу.",
        tone,
        to: null,
      };
    }
    case "assigned_group": {
      const name = str(payload.group_name);
      return {
        title: "Назначена группа",
        description: name ? `Вы назначены куратором группы «${name}».` : "Вы назначены куратором.",
        tone,
        to: null,
      };
    }
    case "hello":
      return {
        title: "Добро пожаловать",
        description: "Это ваше первое уведомление на платформе.",
        tone: "info",
        to: null,
      };
    case "role_changed": {
      const role = str(payload.role);
      return {
        title: "Роль изменена",
        description: role ? `Теперь ваша роль — ${role}.` : "Ваша роль изменена.",
        tone,
        to: null,
      };
    }
    default:
      return {
        title: "Событие",
        description: objectTitle ? `Обновление по «${objectTitle}».` : "Новое событие.",
        tone,
        to: courseTarget,
      };
  }
}

export function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diffSec = Math.round((Date.now() - then) / 1000);
  if (diffSec < 60) return "только что";
  const min = Math.round(diffSec / 60);
  if (min < 60) return `${min} мин назад`;
  const hours = Math.round(min / 60);
  if (hours < 24) return `${hours} ч назад`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} дн назад`;
  return new Date(iso).toLocaleDateString("ru-RU");
}