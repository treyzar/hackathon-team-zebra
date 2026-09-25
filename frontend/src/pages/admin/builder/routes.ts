import type { RouteRecordRaw } from "vue-router";
import AdminBuilderPage from "./AdminBuilderPage.vue";
import { ADMIN_BUILDER_ROUTE } from "./constants";

export const adminBuilderRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_BUILDER_ROUTE,
    component: AdminBuilderPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "Конструктор",
      description: "Выберите курс для редактирования",
    },
  },
];
