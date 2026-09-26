import type { RouteRecordRaw } from "vue-router";

import { navigationByRole } from "@/modules/navigation/items";
import { WORKSPACE_SECTION_PLACEHOLDERS } from "./constants";
import WorkspaceSectionPage from "./WorkspaceSectionPage.vue";

export const workspaceSectionRoutes: RouteRecordRaw[] = WORKSPACE_SECTION_PLACEHOLDERS.map(
  (placeholder) => {
    const item = navigationByRole[placeholder.role].find(
      (entry) => entry.path === placeholder.path,
    );
    return {
      name: placeholder.name,
      path: placeholder.path,
      component: WorkspaceSectionPage,
      meta: {
        requiresAuth: true,
        allowedRoles: [placeholder.role],
        title: item?.label,
        description: item?.description,
      },
    };
  },
);
