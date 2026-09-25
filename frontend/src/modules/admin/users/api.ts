import { api } from "@/api/http";
import type { AdminRole, AdminUser } from "../shared/types";

export const userApi = {
  async users(role?: AdminRole): Promise<AdminUser[]> {
    return (await api.get<AdminUser[]>("/admin/users", { params: role ? { role } : {} })).data;
  },
  async setRole(id: number, role: AdminRole): Promise<AdminUser> {
    return (await api.patch<AdminUser>(`/admin/users/${id}/role`, { role })).data;
  },
};
