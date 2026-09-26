import type { RouteRecordRaw } from "vue-router";

import CuratorDeadlinesPage from "./CuratorDeadlinesPage.vue";
import { CURATOR_DEADLINES_ROUTE } from "./constants";

export const curatorDeadlinesRoutes: RouteRecordRaw[] = [
  {
    ...CURATOR_DEADLINES_ROUTE,
    component: CuratorDeadlinesPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["curator", "admin"],
      title: "Дедлайны",
    },
  },
];
