import { api } from "@/api/http";
import type { QuestionUpdate, StaffQuestion } from "./types";

export const questionApi = {
  async all(): Promise<StaffQuestion[]> {
    const items: StaffQuestion[] = [];
    for (let offset = 0; ; offset += 200) {
      const page = (
        await api.get<StaffQuestion[]>("/questions", { params: { limit: 200, offset } })
      ).data;
      items.push(...page);
      if (page.length < 200) return items;
    }
  },

  async update(id: number, changes: QuestionUpdate): Promise<StaffQuestion> {
    return (await api.patch<StaffQuestion>(`/questions/${id}`, changes)).data;
  },
};
