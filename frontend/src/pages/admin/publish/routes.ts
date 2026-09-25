import type { RouteRecordRaw } from "vue-router";
import AdminPublishPage from "./AdminPublishPage.vue";
import { ADMIN_PUBLISH_ROUTE } from "./constants";

export const adminPublishRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_PUBLISH_ROUTE,
    component: AdminPublishPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "Публикация курса",
      description: "Проверьте структуру и доступность курса",
    },
  },
];
