import { api } from "@/api/http";
import type { AdminCourse, EnrolledStudent, EnrollResult } from "./types";

export const courseEnrollmentApi = {
  async courses(): Promise<AdminCourse[]> {
    return (await api.get<AdminCourse[]>("/admin/courses")).data;
  },

  async enrollments(courseId: number): Promise<EnrolledStudent[]> {
    return (await api.get<EnrolledStudent[]>(`/admin/courses/${courseId}/enrollments`)).data;
  },

  async enrollGroup(courseId: number, groupId: number): Promise<EnrollResult> {
    return (
      await api.post<EnrollResult>(`/admin/courses/${courseId}/enrollments`, {
        user_ids: [],
        group_ids: [groupId],
      })
    ).data;
  },

  async unenrollStudent(courseId: number, userId: number): Promise<void> {
    await api.delete(`/admin/courses/${courseId}/enrollments/${userId}`);
  },
};
