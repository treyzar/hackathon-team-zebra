import type { RouteRecordRaw } from "vue-router";
import { STUDENT_SKILLS_ROUTE } from "./constants";

export const studentSkillsRoutes: RouteRecordRaw[] = [
  {
    ...STUDENT_SKILLS_ROUTE,
    component: () => import("./StudentSkillsPage.vue"),
    meta: {
      requiresAuth: true,
      allowedRoles: ["student"],
      title: "Карта навыков",
      description: "Навыки ваших курсов",
    },
  },
];
