export interface ParsedMethodStep {
  number: string;
  title: string;
  type: string;
  grading: string;
  details: string;
  supported: boolean;
}

export interface ParsedMethod {
  modules: number;
  steps: ParsedMethodStep[];
}

export function parseMethodText(source: string): ParsedMethod {
  const lines = source.split(/\r?\n/).map((line) => line.trim());
  let modules = 0;
  const steps: ParsedMethodStep[] = [];
  let current: ParsedMethodStep | null = null;
  for (const line of lines) {
    if (/^Модуль\s+\d/i.test(line)) modules += 1;
    const stepMatch = line.match(/^Шаг\s+([\d.]+)\s*[.\-–:]?\s*(.+)$/i);
    if (stepMatch) {
      current = {
        number: stepMatch[1]!.replace(/\.$/, ""),
        title: stepMatch[2]!.trim(),
        type: "Не указан",
        grading: "—",
        details: "Текст",
        supported: false,
      };
      steps.push(current);
      continue;
    }
    if (!current) continue;
    if (line.startsWith('Тип шага')) {
      current.type = line.replace(/^Тип шага\s*/i, "").trim() || "Не указан";
      current.supported = /^(теория|контрольный вопрос|вопрос|задача с тестами|проект)$/i.test(current.type);
    }
    if (line.startsWith('Проверка')) current.grading = line.replace(/^Проверка\s*/i, "").trim() || "—";
    if (line.startsWith('Что сдаёт ученик')) current.details = line.replace(/^Что сдаёт ученик\s*/i, "").trim() || "Текст";
  }
  return { modules, steps };
}
