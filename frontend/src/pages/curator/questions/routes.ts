import type { RouteRecordRaw } from "vue-router";

import CuratorQuestionsPage from "./CuratorQuestionsPage.vue";
import { CURATOR_QUESTIONS_ROUTE } from "./constants";

export const curatorQuestionsRoutes: RouteRecordRaw[] = [
  {
    ...CURATOR_QUESTIONS_ROUTE,
    component: CuratorQuestionsPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["curator", "admin"],
      title: "Вопросы",
    },
  },
];
