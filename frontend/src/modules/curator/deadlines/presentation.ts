import { deadlineToInput } from "@/modules/shared/deadline";
import type { DeadlineModule, StepDeadline } from "./types";

const stepTypes: Record<string, string> = {
  theory: "Теория",
  single_choice: "Вопрос",
  multiple_choice: "Вопрос",
  number: "Число",
  short_text: "Короткий ответ",
  free_text: "Проект",
  programming: "Код",
};

export function stepTypeLabel(type: string): string {
  return stepTypes[type] ?? type;
}

export function deadlineDate(value: string | null): string {
  return value?.slice(0, 10) ?? "";
}

export function deadlineTime(value: string | null): string {
  return value?.slice(11, 16) || "23:59";
}

export function withDeadlineDate(value: string | null, date: string): string {
  return date ? `${date}T${deadlineTime(value)}` : "";
}

export function withDeadlineTime(value: string | null, time: string): string {
  return deadlineDate(value) ? `${deadlineDate(value)}T${time}` : "";
}

export function validDeadlineInput(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value) && !Number.isNaN(Date.parse(value));
}

export function deadlineLabel(value: string | null): string {
  if (!value) return "Не установлен";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ownInput(row: StepDeadline): string | null {
  return row.own ? deadlineToInput(row.own.due_at) : null;
}

export function groupSteps(rows: StepDeadline[]): DeadlineModule[] {
  const modules: DeadlineModule[] = [];
  for (const row of rows) {
    let module = modules.find((item) => item.id === row.module_id);
    if (!module) {
      module = {
        id: row.module_id,
        number: modules.length + 1,
        title: row.module_title,
        steps: [],
      };
      modules.push(module);
    }
    module.steps.push({ number: `${module.number}.${module.steps.length + 1}`, deadline: row });
  }
  return modules;
}
