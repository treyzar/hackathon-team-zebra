import type { RouteRecordRaw } from "vue-router";
import AdminCoursesPage from "./AdminCoursesPage.vue";
import { ADMIN_COURSES_ROUTE } from "./constants";

export const adminCoursesRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_COURSES_ROUTE,
    component: AdminCoursesPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "Курсы",
      description: "Черновики и опубликованные программы",
    },
  },
];
