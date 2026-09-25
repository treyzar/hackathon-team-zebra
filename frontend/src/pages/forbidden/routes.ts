import type { RouteRecordRaw } from "vue-router";

import ForbiddenPage from "./ForbiddenPage.vue";
import { FORBIDDEN_ROUTE } from "./constants";

export const forbiddenRoutes: RouteRecordRaw[] = [
  {
    ...FORBIDDEN_ROUTE,
    component: ForbiddenPage,
    meta: {
      requiresAuth: true,
      title: "Нет доступа",
      description: "Этот раздел доступен другой роли",
    },
  },
];
