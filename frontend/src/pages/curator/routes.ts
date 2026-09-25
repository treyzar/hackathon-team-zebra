import type { RouteRecordRaw } from "vue-router";

import { curatorReviewRoutes } from "./review/routes";
import { curatorReviewsRoutes } from "./reviews/routes";

export const curatorRoutes: RouteRecordRaw[] = [...curatorReviewsRoutes, ...curatorReviewRoutes];
