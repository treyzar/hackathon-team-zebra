export function pluralRu(count: number, one: string, few: string, many: string): string {
  const tens = Math.abs(count) % 100;
  const units = tens % 10;
  if (tens >= 11 && tens <= 14) return many;
  if (units === 1) return one;
  if (units >= 2 && units <= 4) return few;
  return many;
}

export function stepsText(count: number): string {
  return `${count} ${pluralRu(count, "шаг", "шага", "шагов")}`;
}

export function modulesText(count: number): string {
  return `${count} ${pluralRu(count, "модуль", "модуля", "модулей")}`;
}
