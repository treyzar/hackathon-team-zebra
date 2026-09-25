import type { RouteRecordRaw } from "vue-router";

import SignupPage from "./SignupPage.vue";
import { SIGNUP_ROUTE } from "./constants";

export const signupRoutes: RouteRecordRaw[] = [
  {
    ...SIGNUP_ROUTE,
    component: SignupPage,
    meta: { guestOnly: true },
  },
];
