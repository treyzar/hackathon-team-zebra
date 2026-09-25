import type { RouteRecordRaw } from "vue-router";

import CuratorReviewsPage from "./CuratorReviewsPage.vue";
import { CURATOR_REVIEWS_ROUTE } from "./constants";

export const curatorReviewsRoutes: RouteRecordRaw[] = [
  {
    ...CURATOR_REVIEWS_ROUTE,
    component: CuratorReviewsPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["curator", "admin"],
      title: "Работы на проверку",
    },
  },
];
