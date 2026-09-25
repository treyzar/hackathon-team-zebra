import type { RouteRecordRaw } from "vue-router";
import AdminRevisionsPage from "./AdminRevisionsPage.vue";
import { ADMIN_REVISIONS_ROUTE } from "./constants";

export const adminRevisionsRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_REVISIONS_ROUTE,
    component: AdminRevisionsPage,
    meta: {
      requiresAuth: true,
      allowedRoles: ["admin"],
      title: "История редакций",
      description: "Сохранённые версии задания",
    },
  },
];
