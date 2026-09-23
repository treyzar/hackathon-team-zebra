import { createRouter, createWebHistory } from "vue-router";
import type { Pinia } from "pinia";

import DashboardPage from "@/pages/DashboardPage.vue";
import LoginPage from "@/pages/LoginPage.vue";
import SignupPage from "@/pages/SignupPage.vue";
import { useAuthStore } from "@/stores/auth";

declare module "vue-router" {
  interface RouteMeta {
    guestOnly?: boolean;
    requiresAuth?: boolean;
  }
}

export function createAppRouter(pinia: Pinia) {
  const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
      {
        path: "/",
        name: "dashboard",
        component: DashboardPage,
        meta: { requiresAuth: true },
      },
      {
        path: "/login",
        name: "login",
        component: LoginPage,
        meta: { guestOnly: true },
      },
      {
        path: "/signup",
        name: "signup",
        component: SignupPage,
        meta: { guestOnly: true },
      },
      {
        path: "/:pathMatch(.*)*",
        redirect: "/",
      },
    ],
  });

  router.beforeEach((to) => {
    const auth = useAuthStore(pinia);

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return { name: "login", query: { redirect: to.fullPath } };
    }

    if (to.meta.guestOnly && auth.isAuthenticated) {
      return { name: "dashboard" };
    }

    return true;
  });

  return router;
}
