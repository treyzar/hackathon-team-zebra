import { api } from "@/api/http";
import type { CourseSkills } from "./types";

export const skillsApi = {
  async map(): Promise<CourseSkills[]> {
    return (await api.get<CourseSkills[]>("/skills")).data;
  },
};
