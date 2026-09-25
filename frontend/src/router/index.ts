import { createRouter, createWebHistory } from "vue-router";
import type { Pinia } from "pinia";

import type { UserRole } from "@/api/http";
import { adminRoutes } from "@/pages/admin/routes";
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
import { dashboardRoutes } from "@/pages/dashboard/routes";
import { FORBIDDEN_ROUTE } from "@/pages/forbidden/constants";
import { forbiddenRoutes } from "@/pages/forbidden/routes";
import { LOGIN_ROUTE } from "@/pages/login/constants";
import { loginRoutes } from "@/pages/login/routes";
import { signupRoutes } from "@/pages/signup/routes";
import { studentRoutes } from "@/pages/student/routes";
import { workspaceSectionRoutes } from "@/pages/workspace-section/routes";
import { useAuthStore } from "@/stores/auth";

declare module "vue-router" {
  interface RouteMeta {
    guestOnly?: boolean;
    requiresAuth?: boolean;
    allowedRoles?: UserRole[];
    title?: string;
    description?: string;
  }
}

export function createAppRouter(pinia: Pinia) {
  const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
      ...dashboardRoutes,
      ...adminRoutes,
      ...studentRoutes,
      ...workspaceSectionRoutes,
      ...forbiddenRoutes,
      ...loginRoutes,
      ...signupRoutes,
      {
        path: "/:pathMatch(.*)*",
        redirect: DASHBOARD_ROUTE.path,
      },
    ],
  });

  router.beforeEach(async (to) => {
    const auth = useAuthStore(pinia);

    if (to.meta.requiresAuth || to.meta.guestOnly) {
      await auth.restoreSession();
    }

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return { name: LOGIN_ROUTE.name, query: { redirect: to.fullPath } };
    }

    if (to.meta.allowedRoles && !auth.hasRole(...to.meta.allowedRoles)) {
      return { name: FORBIDDEN_ROUTE.name };
    }

    if (to.meta.guestOnly && auth.isAuthenticated) {
      return { name: DASHBOARD_ROUTE.name };
    }

    return true;
  });

  return router;
}
