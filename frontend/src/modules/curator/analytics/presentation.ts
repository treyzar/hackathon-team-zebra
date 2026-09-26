import type {
  ModuleAnalytics,
  ModuleStats,
  StepCell,
  StudentAnalytics,
  StudentInfo,
  StudentModule,
  StudentSteps,
} from "./types";

export function studentName(student: StudentInfo): string {
  return (
    [student.surname, student.name, student.patronymic].filter(Boolean).join(" ") ||
    student.username
  );
}

export function studentCourseProgress(student: StudentAnalytics): {
  completed: number;
  total: number;
  percent: number;
} {
  const completed = student.modules.reduce((sum, module) => sum + module.steps_completed, 0);
  const total = student.modules.reduce((sum, module) => sum + module.steps_total, 0);
  return { completed, total, percent: total ? Math.round((100 * completed) / total) : 0 };
}

export function averageProgress(students: StudentAnalytics[]): number | null {
  if (!students.length) return null;
  return Math.round(
    students.reduce((sum, student) => sum + studentCourseProgress(student).percent, 0) /
      students.length,
  );
}

export function lagCounts(students: StudentAnalytics[]): {
  falling: number;
  slowed: number;
  onTrack: number;
} {
  return {
    falling: students.filter((student) => student.lag.status === "falling_behind").length,
    slowed: students.filter((student) => student.lag.status === "slowed").length,
    onTrack: students.filter((student) => student.lag.status === "on_track").length,
  };
}

export function hardestModule(modules: ModuleStats[]): ModuleStats | null {
  return modules.reduce<ModuleStats | null>(
    (lowest, module) =>
      module.first_attempt_percent !== null &&
      (lowest === null ||
        lowest.first_attempt_percent === null ||
        module.first_attempt_percent < lowest.first_attempt_percent)
        ? module
        : lowest,
    null,
  );
}

export function lagLabel(status: StudentAnalytics["lag"]["status"]): string {
  return status === "falling_behind"
    ? "Выпадает"
    : status === "slowed"
      ? "Замедлился"
      : "В графике";
}

export function moduleCell(student: StudentAnalytics, moduleId: number): StudentModule | undefined {
  return student.modules.find((module) => module.module_id === moduleId);
}

export function stepCell(student: StudentSteps, stepId: number): StepCell | undefined {
  return student.steps.find((step) => step.step_id === stepId);
}

export function stepCellStatus(cell: StepCell | undefined): { text: string; tone: string } {
  if (!cell || (cell.state === "not_started" && cell.attempts === 0))
    return { text: "–", tone: "idle" };
  if (cell.has_unresolved_return) return { text: "↺", tone: "return" };
  if (cell.state === "checking") return { text: "◷", tone: "checking" };
  if (cell.completed) return { text: "✓", tone: "passed" };
  if (cell.state === "failed" || cell.state === "attempts_exhausted")
    return { text: `× ${cell.attempts}`, tone: "failed" };
  return { text: `${cell.earned}/${cell.max_score}`, tone: "open" };
}

export function activityLabel(iso: string | null, now = new Date()): string {
  if (!iso) return "не отправлял";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const submitted = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const days = Math.round((today.getTime() - submitted.getTime()) / 86_400_000);
  if (days <= 0) return "сегодня";
  if (days === 1) return "вчера";
  return `${days} дн. назад`;
}

export function studentLastSubmission(student: StudentSteps): string | null {
  return student.steps.reduce<string | null>(
    (latest, cell) =>
      cell.last_submission_at && (!latest || cell.last_submission_at > latest)
        ? cell.last_submission_at
        : latest,
    null,
  );
}

export function stepSummary(
  data: ModuleAnalytics,
  stepId: number,
): {
  total: number;
  submitted: number;
  firstAttempt: number;
  completed: number;
  attempts: number[];
  returned: number;
  failed: number;
  checking: number;
} {
  const cells = data.students
    .map((student) => stepCell(student, stepId))
    .filter((cell) => cell !== undefined);
  return {
    total: data.students.length,
    submitted: cells.filter((cell) => cell.attempts > 0).length,
    firstAttempt: cells.filter((cell) => cell.first_attempt_solved === true).length,
    completed: cells.filter((cell) => cell.completed).length,
    attempts: [1, 2, 3, 4].map(
      (count) =>
        cells.filter((cell) => (count === 4 ? cell.attempts >= 4 : cell.attempts === count)).length,
    ),
    returned: cells.filter((cell) => cell.has_unresolved_return).length,
    failed: cells.filter(
      (cell) =>
        !cell.has_unresolved_return &&
        (cell.state === "failed" || cell.state === "attempts_exhausted"),
    ).length,
    checking: cells.filter((cell) => cell.state === "checking").length,
  };
}

export function stepTypeLabel(type: string): string {
  return (
    {
      theory: "Теория",
      single_choice: "Выбор ответа",
      multiple_choice: "Выбор ответов",
      free_text: "Свободный ответ",
      programming: "Программирование",
    }[type] ?? type
  );
}
