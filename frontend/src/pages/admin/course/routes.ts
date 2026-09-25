import type { RouteRecordRaw } from "vue-router";
import AdminCoursePage from "./AdminCoursePage.vue";
import { ADMIN_COURSE_ROUTE } from "./constants";

export const adminCourseRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_COURSE_ROUTE,
    component: AdminCoursePage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "Конструктор курса",
      description: "Модули, шаги и настройки программы",
    },
  },
];
