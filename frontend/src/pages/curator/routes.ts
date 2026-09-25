import type { RouteRecordRaw } from "vue-router";

import { curatorQuestionsRoutes } from "./questions/routes";
import { curatorReviewRoutes } from "./review/routes";
import { curatorReviewsRoutes } from "./reviews/routes";

export const curatorRoutes: RouteRecordRaw[] = [
  ...curatorReviewsRoutes,
  ...curatorReviewRoutes,
  ...curatorQuestionsRoutes,
];
