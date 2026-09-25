import type { RouteRecordRaw } from "vue-router";
import { studentCourseRoutes } from "./course/routes";
import { studentCoursesRoutes } from "./courses/routes";
import { studentStepRoutes } from "./step/routes";

export const studentRoutes: RouteRecordRaw[] = [
  ...studentCoursesRoutes,
  ...studentCourseRoutes,
  ...studentStepRoutes,
];
