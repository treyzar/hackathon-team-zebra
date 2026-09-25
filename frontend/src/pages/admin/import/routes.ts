import type { RouteRecordRaw } from "vue-router";
import AdminImportPage from "./AdminImportPage.vue";
import { ADMIN_IMPORT_ROUTE } from "./constants";

export const adminImportRoutes: RouteRecordRaw[] = [
  {
    ...ADMIN_IMPORT_ROUTE,
    component: AdminImportPage,
    meta: { requiresAuth: true, allowedRoles: ["admin"], title: "Импорт / экспорт курса" },
  },
];
