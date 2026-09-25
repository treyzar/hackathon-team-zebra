import type { UserRole } from "@/api/http";

export const WORKSPACE_SECTION_ROUTES = {
  studentSkills: { name: "student-skills", path: "/student/skills" },
  studentHistory: { name: "student-history", path: "/student/history" },
  studentProgress: { name: "student-progress", path: "/student/progress" },
  curatorLearners: { name: "curator-learners", path: "/curator/learners" },
} as const;

export const WORKSPACE_SECTION_PLACEHOLDERS: { role: UserRole; name: string; path: string }[] = [
  { role: "student", ...WORKSPACE_SECTION_ROUTES.studentSkills },
  { role: "student", ...WORKSPACE_SECTION_ROUTES.studentHistory },
  { role: "student", ...WORKSPACE_SECTION_ROUTES.studentProgress },
  { role: "curator", ...WORKSPACE_SECTION_ROUTES.curatorLearners },
];
