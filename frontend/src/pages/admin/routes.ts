import type { RouteRecordRaw } from "vue-router";
import { adminBuilderRoutes } from "./builder/routes";
import { adminCourseRoutes } from "./course/routes";
import { adminCoursesRoutes } from "./courses/routes";
import { adminImportRoutes } from "./import/routes";
import { adminPublishRoutes } from "./publish/routes";
import { adminRevisionsRoutes } from "./revisions/routes";
import { adminStepRoutes } from "./step/routes";

export const adminRoutes: RouteRecordRaw[] = [
  ...adminBuilderRoutes,
  ...adminCourseRoutes,
  ...adminCoursesRoutes,
  ...adminImportRoutes,
  ...adminPublishRoutes,
  ...adminRevisionsRoutes,
  ...adminStepRoutes,
];
