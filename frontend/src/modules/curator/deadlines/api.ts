import { api } from "@/api/http";
import type { Course, CourseListItem, StudentStep } from "@/modules/student/courses/types";
import type { DeadlineGroup, OwnDeadline, StepDeadlineResponse } from "./types";

export const deadlinesApi = {
  async courses(): Promise<CourseListItem[]> {
    return (await api.get<CourseListItem[]>("/courses")).data;
  },
  async groups(): Promise<DeadlineGroup[]> {
    return (await api.get<DeadlineGroup[]>("/groups")).data;
  },
  async steps(groupId: number, courseId: number): Promise<StepDeadlineResponse[]> {
    return (
      await api.get<StepDeadlineResponse[]>(`/groups/${groupId}/courses/${courseId}/deadlines`)
    ).data;
  },
  async course(courseId: number): Promise<Course> {
    return (await api.get<Course>(`/courses/${courseId}`)).data;
  },
  async step(stepId: number): Promise<StudentStep> {
    return (await api.get<StudentStep>(`/steps/${stepId}`)).data;
  },
  async setStep(groupId: number, stepId: number, dueAt: string): Promise<OwnDeadline> {
    return (await api.put<OwnDeadline>(`/groups/${groupId}/deadlines/${stepId}`, { due_at: dueAt }))
      .data;
  },
  async removeStep(groupId: number, stepId: number): Promise<void> {
    await api.delete(`/groups/${groupId}/deadlines/${stepId}`);
  },
};
