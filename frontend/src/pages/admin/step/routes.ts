import type { RouteRecordRaw } from "vue-router";
import AdminStepPage from "./AdminStepPage.vue";
import { ADMIN_STEP_NEW_ROUTE, ADMIN_STEP_ROUTE } from "./constants";

export const adminStepRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_STEP_ROUTE,
    component: AdminStepPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "Редактор шага",
      description: "Содержание, ответы и проверка",
    },
  },
  {
    ...ADMIN_STEP_NEW_ROUTE,
    component: AdminStepPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "Новый шаг",
      description: "Выберите тип задания и заполните его",
    },
  },
];
