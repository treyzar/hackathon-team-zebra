import type { RouteRecordRaw } from "vue-router";

import CuratorReviewPage from "./CuratorReviewPage.vue";
import { CURATOR_REVIEW_ROUTE } from "./constants";

export const curatorReviewRoutes: RouteRecordRaw[] = [
  {
    ...CURATOR_REVIEW_ROUTE,
    component: CuratorReviewPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["curator", "admin"],
      title: "Проверка работы",
    },
  },
];
