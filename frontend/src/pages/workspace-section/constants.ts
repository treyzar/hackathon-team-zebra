import type { UserRole } from "@/api/http";

export const WORKSPACE_SECTION_ROUTES = {
  studentHistory: { name: "student-history", path: "/student/history" },
  studentProgress: { name: "student-progress", path: "/student/progress" },
} as const;

export const WORKSPACE_SECTION_PLACEHOLDERS: { role: UserRole; name: string; path: string }[] = [
  { role: "student", ...WORKSPACE_SECTION_ROUTES.studentHistory },
  { role: "student", ...WORKSPACE_SECTION_ROUTES.studentProgress },
];
