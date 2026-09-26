import type { GroupRatingRow } from "./types";

/** What the rating is made of: "Python 6 · Алгоритмы 4 · серия 3 дн. +6". */
export function ratingParts(row: GroupRatingRow): string {
  const parts = row.courses.map((course) => `${course.title} ${course.points}`);
  if (row.streak.days) parts.push(`серия ${row.streak.days} дн. +${row.streak.bonus}`);
  return parts.length ? parts.join(" · ") : "Нет курсов";
}

/** Members by place in the rating; those missing from it keep their order
 * at the end. */
export function orderByRating<T extends { id: number }>(
  members: T[],
  rows: GroupRatingRow[] | null,
): T[] {
  if (!rows) return members;
  const place = new Map(rows.map((row) => [row.student_id, row.place]));
  const rank = (member: T) => place.get(member.id) ?? Number.POSITIVE_INFINITY;
  return members
    .map((member, index) => ({ member, index }))
    .sort((a, b) => rank(a.member) - rank(b.member) || a.index - b.index)
    .map(({ member }) => member);
}
