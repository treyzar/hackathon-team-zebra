import type { RouteRecordRaw } from "vue-router";
import { STUDENT_COURSE_ROUTE } from "./constants";

export const studentCourseRoutes: RouteRecordRaw[] = [
  {
    ...STUDENT_COURSE_ROUTE,
    component: () => import("./StudentCoursePage.vue"),
    props: (route) => ({ courseId: Number(route.params.courseId) }),
    meta: {
      requiresAuth: true,
      allowedRoles: ["student"],
      title: "Курсы",
      description: "Содержание курса и ваши шаги",
    },
  },
];
