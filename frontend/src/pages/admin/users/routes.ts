import type { RouteRecordRaw } from "vue-router";
import AdminUsersPage from "./AdminUsersPage.vue";
import { ADMIN_USERS_ROUTE } from "./constants";

export const adminUsersRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_USERS_ROUTE,
    component: AdminUsersPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "Пользователи",
      description: "Участники платформы и их роли",
    },
  },
];
