import { api } from "@/api/http";
import type { LearnerGroup } from "./types";

export const learnersApi = {
  /** The curator's groups (all of them for an admin) with students. */
  async groups(): Promise<LearnerGroup[]> {
    return (await api.get<LearnerGroup[]>("/learners")).data;
  },
};
