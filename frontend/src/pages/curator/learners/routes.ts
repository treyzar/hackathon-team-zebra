import type { RouteRecordRaw } from "vue-router";

import CuratorLearnersPage from "./CuratorLearnersPage.vue";
import { CURATOR_LEARNERS_ROUTE } from "./constants";

export const curatorLearnersRoutes: RouteRecordRaw[] = [
  {
    ...CURATOR_LEARNERS_ROUTE,
    component: CuratorLearnersPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["curator", "admin"],
      title: "Ученики",
    },
  },
];
