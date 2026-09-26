import type { CourseSkills, Skill, SkillState } from "./types";

// Honeycomb geometry, in pixels: a cell is 130×112; columns step by 98 and
// every odd column is shifted down by half a cell.
export const HEX = { width: 130, height: 112, column: 98, row: 114, padX: 40, padY: 48 };
// Cells per column: courses grow to the right.
export const ROWS = 4;

export interface HexCell {
  key: string;
  x: number;
  y: number;
  courseId: number;
  skill: Skill;
}

export interface HexLabel {
  text: string;
  title: string;
  x: number;
  y: number;
  // The label never gets wider than its course's band.
  width: number;
}

// A course label is 12px bold capitals with letter spacing: about 9px a
// letter. Enough to keep labels of neighbouring bands apart.
const LABEL_LETTER = 9;
// The widest band a long name may claim; beyond it the name is cut.
const MAX_LABEL_COLUMNS = 4;

function position(column: number, row: number): { x: number; y: number } {
  return {
    x: HEX.padX + column * HEX.column,
    y: HEX.padY + row * HEX.row + (column % 2 ? HEX.row / 2 : 0),
  };
}

function bandWidth(columns: number): number {
  return (columns - 1) * HEX.column + HEX.width;
}

/** Columns a course takes: enough for its skills and for its name. */
export function bandColumns(title: string, skills: number): number {
  const forSkills = Math.max(1, Math.ceil(skills / ROWS));
  let forLabel = 1;
  while (forLabel < MAX_LABEL_COLUMNS && bandWidth(forLabel) < title.length * LABEL_LETTER)
    forLabel += 1;
  return Math.max(forSkills, forLabel);
}

/** Each course is a band of columns with its name above it; only the
 * student's own courses are on the map. */
export function hexLayout(courses: CourseSkills[]): {
  cells: HexCell[];
  labels: HexLabel[];
  width: number;
  height: number;
} {
  const cells: HexCell[] = [];
  const labels: HexLabel[] = [];
  let column = 0;
  for (const course of courses) {
    const columns = bandColumns(course.title, course.skills.length);
    labels.push({
      text: course.title.toUpperCase(),
      title: course.title,
      x: position(column, 0).x,
      y: 14,
      // Up to the next band, which starts one column step further.
      width: columns * HEX.column - 8,
    });
    course.skills.forEach((skill, index) => {
      cells.push({
        key: `${course.course_id}-${index}`,
        courseId: course.course_id,
        skill,
        ...position(column + Math.floor(index / ROWS), index % ROWS),
      });
    });
    column += columns;
  }
  return {
    cells,
    labels,
    width: HEX.padX * 2 + Math.max(0, column - 1) * HEX.column + HEX.width,
    height: HEX.padY + (ROWS - 1) * HEX.row + HEX.row / 2 + HEX.height + 24,
  };
}

export const skillIcons: Record<SkillState, string> = {
  gold: "★",
  done: "✓",
  in_progress: "●",
  open: "○",
  locked: "",
};

/** The line under a skill's name: "2 из 6 · ↺ 1", "после «Основы»". */
export function skillSub(skill: Skill): string {
  if (skill.state === "locked")
    return skill.opens_after ? `после «${skill.opens_after}»` : "закрыто";
  if (!skill.steps_total) return "шагов пока нет";
  const done = `${skill.steps_completed} из ${skill.steps_total}`;
  return skill.steps_returned ? `${done} · ↺ ${skill.steps_returned}` : done;
}

export function skillAbout(skill: Skill, courseTitle: string): string {
  const where = `Модуль «${skill.module_title}» курса «${courseTitle}».`;
  if (skill.state === "gold") return `${where} Все задания решены с первой попытки на максимум.`;
  if (skill.state === "done") return `${where} Навык освоен.`;
  if (skill.state === "locked")
    return `${where} Откроется после модуля «${skill.opens_after ?? "перед ним"}».`;
  return where;
}

export type SegmentKind = "completed" | "checking" | "returned" | "ahead";

/** One bar segment per step of the module, in the order of the legend. */
export function skillSegments(skill: Skill): SegmentKind[] {
  const ahead = Math.max(
    0,
    skill.steps_total - skill.steps_completed - skill.steps_checking - skill.steps_returned,
  );
  return [
    ...Array<SegmentKind>(skill.steps_completed).fill("completed"),
    ...Array<SegmentKind>(skill.steps_checking).fill("checking"),
    ...Array<SegmentKind>(skill.steps_returned).fill("returned"),
    ...Array<SegmentKind>(ahead).fill("ahead"),
  ];
}

/** "2 зачтено · 1 на проверке · 1 возвращено · 2 впереди". */
export function skillCountsText(skill: Skill): string {
  const counts = skillSegments(skill).reduce((acc, kind) => ({ ...acc, [kind]: acc[kind] + 1 }), {
    completed: 0,
    checking: 0,
    returned: 0,
    ahead: 0,
  } as Record<SegmentKind, number>);
  return [
    `${counts.completed} зачтено`,
    counts.checking ? `${counts.checking} на проверке` : "",
    counts.returned ? `${counts.returned} возвращено` : "",
    `${counts.ahead} впереди`,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** The skill to show first: where the student is now, else the first one. */
export function initialSkill(courses: CourseSkills[]): { courseId: number; index: number } | null {
  for (const course of courses) {
    const index = course.skills.findIndex((skill) => skill.current);
    if (index >= 0) return { courseId: course.course_id, index };
  }
  const first = courses.find((course) => course.skills.length);
  return first ? { courseId: first.course_id, index: 0 } : null;
}
