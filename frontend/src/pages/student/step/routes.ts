import type { RouteRecordRaw } from "vue-router";
import { STUDENT_STEP_ROUTE } from "./constants";

export const studentStepRoutes: RouteRecordRaw[] = [
  {
    ...STUDENT_STEP_ROUTE,
    component: () => import("./StudentStepPage.vue"),
    props: (route) => ({
      courseId: Number(route.params.courseId),
      stepId: Number(route.params.stepId),
    }),
    meta: {
      requiresAuth: true,
      allowedRoles: ["student"],
      title: "Курсы",
      description: "Содержание курса и ваши шаги",
    },
  },
];
