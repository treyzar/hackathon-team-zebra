import type { RouteRecordRaw } from "vue-router";

import DashboardPage from "./DashboardPage.vue";
import { DASHBOARD_ROUTE } from "./constants";

export const dashboardRoutes: RouteRecordRaw[] = [
  {
    ...DASHBOARD_ROUTE,
    component: DashboardPage,
    meta: { requiresAuth: true },
  },
];
