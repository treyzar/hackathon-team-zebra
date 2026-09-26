import type { RouteRecordRaw } from "vue-router";

import { curatorAnalyticsRoutes } from "./analytics/routes";
import { curatorDeadlinesRoutes } from "./deadlines/routes";
import { curatorQuestionsRoutes } from "./questions/routes";
import { curatorReviewRoutes } from "./review/routes";
import { curatorReviewsRoutes } from "./reviews/routes";

export const curatorRoutes: RouteRecordRaw[] = [
  ...curatorReviewsRoutes,
  ...curatorReviewRoutes,
  ...curatorQuestionsRoutes,
  ...curatorAnalyticsRoutes,
  ...curatorDeadlinesRoutes,
];
