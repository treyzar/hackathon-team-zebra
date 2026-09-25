import type { RouteRecordRaw } from "vue-router";
import { STUDENT_COURSES_ROUTE } from "./constants";

export const studentCoursesRoutes: RouteRecordRaw[] = [
  {
    ...STUDENT_COURSES_ROUTE,
    component: () => import("./StudentCoursesPage.vue"),
    meta: {
      requiresAuth: true,
      allowedRoles: ["student"],
      title: "Мои курсы",
      description: "Курсы, шаги и ваш прогресс",
    },
  },
];
