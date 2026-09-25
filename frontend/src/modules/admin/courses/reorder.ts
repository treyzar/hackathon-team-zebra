export function reorderIds(
  ids: readonly number[],
  sourceId: number,
  targetId: number,
  after: boolean,
): number[] {
  const next = [...ids];
  const sourceIndex = next.indexOf(sourceId);
  if (sourceIndex < 0 || !next.includes(targetId) || sourceId === targetId) return next;

  next.splice(sourceIndex, 1);
  next.splice(next.indexOf(targetId) + Number(after), 0, sourceId);
  return next;
}
