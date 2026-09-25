import { api } from "@/api/http";
import type { Revision, RevisionSummary, Step, StepSave } from "../shared/types";

export const stepApi = {
  async step(id: number): Promise<Step> {
    return (await api.get<Step>(`/admin/steps/${id}`)).data;
  },
  async createStep(moduleId: number, data: StepSave): Promise<Step> {
    return (await api.post<Step>(`/admin/modules/${moduleId}/steps`, data)).data;
  },
  async saveStep(id: number, data: StepSave): Promise<Step> {
    return (await api.post<Step>(`/admin/steps/${id}/revisions`, data)).data;
  },
  async setStepHidden(id: number, is_hidden: boolean): Promise<void> {
    await api.patch(`/admin/steps/${id}`, { is_hidden });
  },
  async deleteStep(id: number): Promise<void> {
    await api.delete(`/admin/steps/${id}`);
  },
  async revisions(id: number): Promise<RevisionSummary[]> {
    return (await api.get<RevisionSummary[]>(`/admin/steps/${id}/revisions`)).data;
  },
  async revision(id: number, number: number): Promise<Revision> {
    return (await api.get<Revision>(`/admin/steps/${id}/revisions/${number}`)).data;
  },
};
