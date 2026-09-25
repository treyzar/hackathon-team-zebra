import type { RouteRecordRaw } from "vue-router";
import { adminBuilderRoutes } from "./builder/routes";
import { adminCourseRoutes } from "./course/routes";
import { adminCoursesRoutes } from "./courses/routes";
import { adminGroupsRoutes } from "./groups/routes";
import { adminImportRoutes } from "./import/routes";
import { adminPublishRoutes } from "./publish/routes";
import { adminRevisionsRoutes } from "./revisions/routes";
import { adminStepRoutes } from "./step/routes";
import { adminUsersRoutes } from "./users/routes";

export const adminRoutes: RouteRecordRaw[] = [
  ...adminBuilderRoutes,
  ...adminCourseRoutes,
  ...adminCoursesRoutes,
  ...adminGroupsRoutes,
  ...adminImportRoutes,
  ...adminPublishRoutes,
  ...adminRevisionsRoutes,
  ...adminStepRoutes,
  ...adminUsersRoutes,
];
