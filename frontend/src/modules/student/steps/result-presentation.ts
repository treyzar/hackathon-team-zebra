import { submissionLabel } from "@/modules/student/courses/presentation";

export interface TestRun {
  verdict?: string;
  stdout?: string | null;
  stderr?: string | null;
  expected?: string | null;
}

export interface TestGroup {
  name?: string;
  passed?: boolean;
  earned?: number | null;
  points?: number | null;
  tests?: TestRun[];
}

const verdictLabels: Record<string, string> = {
  ok: "верно",
  wrong_answer: "неверный ответ",
  time_limit: "превышено время",
  compilation_error: "ошибка компиляции",
  runtime_error: "ошибка выполнения",
};

export function verdictLabel(verdict: string | undefined): string {
  return verdict ? (verdictLabels[verdict] ?? "неизвестная ошибка") : "нет результата";
}

export function sampleResults(details: Record<string, unknown>): TestRun[] {
  return Array.isArray(details.samples) ? (details.samples as TestRun[]) : [];
}

export function testGroups(details: Record<string, unknown>): TestGroup[] {
  return Array.isArray(details.groups) ? (details.groups as TestGroup[]) : [];
}

export function failedTests(group: TestGroup): { number: number; verdict: string }[] {
  return (group.tests ?? []).flatMap((test, index) =>
    test.verdict && test.verdict !== "ok"
      ? [{ number: index + 1, verdict: verdictLabel(test.verdict) }]
      : [],
  );
}

export function groupStatus(group: TestGroup): string {
  if (group.passed) return "пройдена";
  const reasons = new Set(failedTests(group).map((test) => test.verdict));
  return reasons.size === 1 ? [...reasons][0]! : "не пройдена";
}

export function resultStatus(status: string, details: Record<string, unknown>): string {
  if (status !== "wrong") return submissionLabel(status);
  const verdicts = [
    ...sampleResults(details).map((sample) => sample.verdict),
    ...testGroups(details).flatMap((group) => (group.tests ?? []).map((test) => test.verdict)),
  ];
  for (const verdict of ["compilation_error", "runtime_error", "time_limit", "wrong_answer"]) {
    if (verdicts.includes(verdict)) {
      const label = verdictLabel(verdict);
      return label[0]!.toUpperCase() + label.slice(1);
    }
  }
  return submissionLabel(status);
}
