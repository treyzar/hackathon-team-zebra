import type { RouteRecordRaw } from "vue-router";
import AdminGroupsPage from "./AdminGroupsPage.vue";
import { ADMIN_GROUPS_ROUTE } from "./constants";

export const adminGroupsRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_GROUPS_ROUTE,
    component: AdminGroupsPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "Группы",
      description: "Состав групп и кураторы",
    },
  },
];
