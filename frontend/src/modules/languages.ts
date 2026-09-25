// Programming languages a step may allow. Keys must match `Language` in
// backend/src/languages.py: the backend rejects any other key.
export type ProgrammingLanguage = "python3" | "javascript" | "cpp" | "csharp" | "go" | "pascal";

export interface LanguageInfo {
  title: string;
  // Monaco language id, for syntax highlighting.
  editor: string;
  fileName: string;
}

export const LANGUAGES: Record<ProgrammingLanguage, LanguageInfo> = {
  python3: { title: "Python 3", editor: "python", fileName: "main.py" },
  javascript: { title: "JavaScript (Node.js)", editor: "javascript", fileName: "main.js" },
  cpp: { title: "C++ (GCC)", editor: "cpp", fileName: "main.cpp" },
  csharp: { title: "C#", editor: "csharp", fileName: "Main.cs" },
  go: { title: "Go", editor: "go", fileName: "main.go" },
  pascal: { title: "Pascal (FPC)", editor: "pascal", fileName: "main.pas" },
};

export const LANGUAGE_KEYS = Object.keys(LANGUAGES) as ProgrammingLanguage[];

export function isLanguage(value: unknown): value is ProgrammingLanguage {
  return typeof value === "string" && value in LANGUAGES;
}

/** Allowed languages of a stored step: old revisions have a single `language`. */
export function stepLanguages(content: Record<string, unknown>): ProgrammingLanguage[] {
  const raw = Array.isArray(content.languages) ? content.languages : [content.language];
  const known = raw.filter(isLanguage);
  return known.length ? known : ["python3"];
}
