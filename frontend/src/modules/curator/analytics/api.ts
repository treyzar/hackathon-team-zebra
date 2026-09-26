import { api } from "@/api/http";
import type { Course, CourseListItem } from "@/modules/student/courses/types";
import type { AnalyticsGroup, CourseAnalytics, ModuleAnalytics } from "./types";

export const analyticsApi = {
  async courses(): Promise<CourseListItem[]> {
    return (await api.get<CourseListItem[]>("/courses")).data;
  },

  async groups(): Promise<AnalyticsGroup[]> {
    return (await api.get<AnalyticsGroup[]>("/groups")).data;
  },

  async course(id: number): Promise<Course> {
    return (await api.get<Course>(`/courses/${id}`)).data;
  },

  async courseAnalytics(groupId: number, courseId: number): Promise<CourseAnalytics> {
    return (await api.get<CourseAnalytics>(`/groups/${groupId}/courses/${courseId}/analytics`))
      .data;
  },

  async moduleAnalytics(
    groupId: number,
    courseId: number,
    moduleId: number,
  ): Promise<ModuleAnalytics> {
    return (
      await api.get<ModuleAnalytics>(
        `/groups/${groupId}/courses/${courseId}/modules/${moduleId}/analytics`,
      )
    ).data;
  },
};
