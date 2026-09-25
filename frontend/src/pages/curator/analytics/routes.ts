import type { RouteRecordRaw } from "vue-router";

import CuratorAnalyticsPage from "./CuratorAnalyticsPage.vue";
import { CURATOR_ANALYTICS_ROUTE } from "./constants";

export const curatorAnalyticsRoutes: RouteRecordRaw[] = [
  {
    ...CURATOR_ANALYTICS_ROUTE,
    component: CuratorAnalyticsPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["curator", "admin"],
      title: "Аналитика",
    },
  },
];
