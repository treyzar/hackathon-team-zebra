import { api } from "@/api/http";
import type { Course, CourseTree, Module, StepAccess } from "../shared/types";

export interface CourseImportResult {
  course_id: number;
  slug: string;
  title: string;
  warnings: string[];
}

export const courseApi = {
  async courses(): Promise<Course[]> {
    return (await api.get<Course[]>("/admin/courses")).data;
  },
  async course(id: number): Promise<CourseTree> {
    return (await api.get<CourseTree>(`/admin/courses/${id}`)).data;
  },
  async createCourse(data: {
    slug: string;
    title: string;
    description: object;
    step_access: StepAccess;
    deadline_at?: string | null;
  }): Promise<Course> {
    return (await api.post<Course>("/admin/courses", data)).data;
  },
  async updateCourse(
    id: number,
    data: Partial<
      Pick<
        Course,
        "slug" | "title" | "description" | "step_access" | "is_published" | "deadline_at"
      >
    >,
  ): Promise<Course> {
    return (await api.patch<Course>(`/admin/courses/${id}`, data)).data;
  },
  async deleteCourse(id: number): Promise<void> {
    await api.delete(`/admin/courses/${id}`);
  },
  async importCourse(file: File): Promise<CourseImportResult> {
    const data = new FormData();
    data.append("file", file);
    return (await api.post<CourseImportResult>("/admin/courses/import", data)).data;
  },
  async exportCourseJson(id: number): Promise<Blob> {
    return (await api.get<Blob>(`/admin/courses/${id}/export`, { responseType: "blob" })).data;
  },
  async exportCoursePdf(id: number): Promise<Blob> {
    return (await api.get<Blob>(`/admin/courses/${id}/export_pdf`, { responseType: "blob" })).data;
  },
  async createModule(courseId: number, title: string): Promise<Module> {
    return (await api.post<Module>(`/admin/courses/${courseId}/modules`, { title })).data;
  },
  async renameModule(id: number, title: string): Promise<void> {
    await api.patch(`/admin/modules/${id}`, { title });
  },
  async deleteModule(id: number): Promise<void> {
    await api.delete(`/admin/modules/${id}`);
  },
  async orderModules(courseId: number, ids: number[]): Promise<void> {
    await api.put(`/admin/courses/${courseId}/modules/order`, { ids });
  },
  async orderSteps(moduleId: number, ids: number[]): Promise<void> {
    await api.put(`/admin/modules/${moduleId}/steps/order`, { ids });
  },
};
