import type { RouteRecordRaw } from "vue-router";

import type { UserRole } from "@/api/http";
import { navigationByRole } from "@/modules/navigation/items";
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
import WorkspaceSectionPage from "./WorkspaceSectionPage.vue";

export const workspaceSectionRoutes: RouteRecordRaw[] = (
  Object.entries(navigationByRole) as [UserRole, (typeof navigationByRole)[UserRole]][]
).flatMap(([role, items]) =>
  (role === "admin" ? [] : items)
    .filter((item) => item.path !== DASHBOARD_ROUTE.path)
    .map((item) => ({
      name: item.name,
      path: item.path,
      component: WorkspaceSectionPage,
      meta: {
        requiresAuth: true,
        allowedRoles: [role],
        title: item.label,
        description: item.description,
      },
    })),
);
