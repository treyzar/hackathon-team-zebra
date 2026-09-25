import type { RouteRecordRaw } from "vue-router";

import LoginPage from "./LoginPage.vue";
import { LOGIN_ROUTE } from "./constants";

export const loginRoutes: RouteRecordRaw[] = [
  {
    ...LOGIN_ROUTE,
    component: LoginPage,
    meta: { guestOnly: true },
  },
];
