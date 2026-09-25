import { api } from "@/api/http";
import type { CourseQueue, ReviewDetail, ReviewFile, ReviewListItem, ReviewVerdict } from "./types";

export const reviewApi = {
  async courses(): Promise<CourseQueue[]> {
    return (await api.get<CourseQueue[]>("/review/courses", { params: { per_course: 200 } })).data;
  },

  async pendingForCourse(courseId: number): Promise<ReviewListItem[]> {
    const items: ReviewListItem[] = [];
    for (let offset = 0; ; offset += 200) {
      const page = (
        await api.get<ReviewListItem[]>("/review/submissions", {
          params: { course_id: courseId, status: "pending_review", limit: 200, offset },
        })
      ).data;
      items.push(...page);
      if (page.length < 200) return items;
    }
  },

  async detail(id: number): Promise<ReviewDetail> {
    return (await api.get<ReviewDetail>(`/review/submissions/${id}`)).data;
  },

  async save(id: number, verdict: ReviewVerdict): Promise<ReviewDetail> {
    return (await api.post<ReviewDetail>(`/review/submissions/${id}`, verdict)).data;
  },

  async file(id: number): Promise<ReviewFile> {
    return (await api.get<ReviewFile>(`/files/${id}`)).data;
  },
};
