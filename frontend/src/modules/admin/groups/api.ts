import { api } from "@/api/http";
import type { AdminUser, Group } from "../shared/types";
import type { GroupRatingRow } from "./types";

export const groupApi = {
  async groups(): Promise<Group[]> {
    return (await api.get<Group[]>("/admin/groups")).data;
  },

  async createGroup(data: { name: string; curator_id: number | null }): Promise<Group> {
    return (await api.post<Group>("/admin/groups", data)).data;
  },

  async updateGroup(id: number, data: { name: string; curator_id: number | null }): Promise<Group> {
    return (await api.patch<Group>(`/admin/groups/${id}`, data)).data;
  },

  async deleteGroup(id: number): Promise<void> {
    await api.delete(`/admin/groups/${id}`);
  },

  async groupStudents(id: number): Promise<AdminUser[]> {
    return (await api.get<AdminUser[]>(`/admin/groups/${id}/students`)).data;
  },

  async addStudent(groupId: number, userId: number): Promise<void> {
    await api.put(`/admin/groups/${groupId}/students/${userId}`);
  },

  async rating(groupId: number): Promise<GroupRatingRow[]> {
    return (await api.get<GroupRatingRow[]>(`/groups/${groupId}/rating`)).data;
  },

  async removeStudent(groupId: number, userId: number): Promise<void> {
    await api.delete(`/admin/groups/${groupId}/students/${userId}`);
  },
};
