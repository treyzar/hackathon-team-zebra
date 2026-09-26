import { studentName } from "../analytics/presentation";
import type { LagStatus, Learner } from "./types";

// Who needs attention first: falling behind, slowed, on track, no courses.
const RANK: Record<LagStatus, number> = { falling_behind: 0, slowed: 1, on_track: 2 };

function rank(learner: Learner): number {
  return learner.status ? RANK[learner.status] : 3;
}

export function sortLearners(students: Learner[]): Learner[] {
  return [...students].sort(
    (a, b) => rank(a) - rank(b) || studentName(a).localeCompare(studentName(b), "ru"),
  );
}

export function statusCounts(students: Learner[]): Record<LagStatus, number> {
  const counts: Record<LagStatus, number> = { falling_behind: 0, slowed: 0, on_track: 0 };
  for (const student of students) if (student.status) counts[student.status] += 1;
  return counts;
}

/** "просрочено шагов: 2"; empty when nothing is overdue. */
export function overdueText(count: number): string {
  return count ? `просрочено шагов: ${count}` : "";
}
