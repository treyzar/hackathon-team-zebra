// gold: every step of the module completed, every task at full score on the
// first attempt; done: every step completed; in_progress: some work sent;
// open: can be started; locked: opens after the previous module.
export type SkillState = "gold" | "done" | "in_progress" | "open" | "locked";

export interface Skill {
  name: string;
  module_id: number;
  module_title: string;
  state: SkillState;
  steps_total: number;
  steps_completed: number;
  steps_checking: number;
  steps_returned: number;
  // The first open step of the module still to do.
  next_step_id: number | null;
  // The student's next step in the course is in this module.
  current: boolean;
  // For a locked module: the module to finish first.
  opens_after: string | null;
}

export interface CourseSkills {
  course_id: number;
  title: string;
  skills: Skill[];
}
