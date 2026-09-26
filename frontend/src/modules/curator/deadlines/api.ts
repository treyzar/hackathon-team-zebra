import { api } from "@/api/http";
import type { CourseListItem } from "@/modules/student/courses/types";
import type { CourseDeadlineState, DeadlineGroup, OwnDeadline, StepDeadline } from "./types";

export const deadlinesApi = {
  async courses(): Promise<CourseListItem[]> {
    return (await api.get<CourseListItem[]>("/courses")).data;
  },
  async groups(): Promise<DeadlineGroup[]> {
    return (await api.get<DeadlineGroup[]>("/groups")).data;
  },
  async steps(groupId: number, courseId: number): Promise<StepDeadline[]> {
    return (await api.get<StepDeadline[]>(`/groups/${groupId}/courses/${courseId}/deadlines`)).data;
  },
  async course(groupId: number, courseId: number): Promise<CourseDeadlineState> {
    return (await api.get<CourseDeadlineState>(`/groups/${groupId}/courses/${courseId}/deadline`))
      .data;
  },
  async setCourse(groupId: number, courseId: number, dueAt: string): Promise<CourseDeadlineState> {
    return (
      await api.put<CourseDeadlineState>(`/groups/${groupId}/courses/${courseId}/deadline`, {
        due_at: dueAt,
      })
    ).data;
  },
  async removeCourse(groupId: number, courseId: number): Promise<void> {
    await api.delete(`/groups/${groupId}/courses/${courseId}/deadline`);
  },
  async setStep(groupId: number, stepId: number, dueAt: string): Promise<OwnDeadline> {
    return (await api.put<OwnDeadline>(`/groups/${groupId}/deadlines/${stepId}`, { due_at: dueAt }))
      .data;
  },
  async removeStep(groupId: number, stepId: number): Promise<void> {
    await api.delete(`/groups/${groupId}/deadlines/${stepId}`);
  },
};
