import axios from "axios";
import { api } from "@/api/http";
import type {
  Course,
  CourseListItem,
  CourseProgress,
  MyRating,
  StudentStep,
  Submission,
  StudentNotification,
  StudentQuestion,
} from "./types";

export const studentCourseApi = {
  async listCourses(): Promise<CourseListItem[]> {
    return (await api.get<CourseListItem[]>("/courses")).data;
  },

  async getCourse(id: number): Promise<Course> {
    return (await api.get<Course>(`/courses/${id}`)).data;
  },

  async getProgress(courseId: number): Promise<CourseProgress> {
    return (await api.get<CourseProgress>(`/courses/${courseId}/progress`)).data;
  },

  async getRating(): Promise<MyRating> {
    return (await api.get<MyRating>("/rating")).data;
  },

  async listNotifications(
    options: { limit?: number; unreadOnly?: boolean } = {},
  ): Promise<StudentNotification[]> {
    return (
      await api.get<StudentNotification[]>("/notifications", {
        params: {
          limit: options.limit ?? 2,
          unread_only: options.unreadOnly ?? false,
          offset: 0,
        },
      })
    ).data;
  },

  async getStep(id: number): Promise<StudentStep> {
    return (await api.get<StudentStep>(`/steps/${id}`)).data;
  },

  async getSubmissions(id: number): Promise<Submission[]> {
    return (await api.get<Submission[]>(`/steps/${id}/submissions`)).data;
  },

  async getSubmission(id: number): Promise<Submission> {
    return (await api.get<Submission>(`/submissions/${id}`)).data;
  },

  async submitAnswer(id: number, answer: Record<string, unknown>): Promise<Submission> {
    return (await api.post<Submission>(`/steps/${id}/submissions`, { answer })).data;
  },

  async getAnswer(id: number): Promise<Record<string, unknown>> {
    return (await api.get<Record<string, unknown>>(`/steps/${id}/answer`)).data;
  },

  async getContentFileUrl(id: number): Promise<string> {
    return (await api.get<{ download_url: string }>(`/files/${id}`)).data.download_url;
  },

  async uploadSubmissionFile(file: File): Promise<number> {
    const mime = file.type || "application/octet-stream";
    const { data: ticket } = await api.post<{
      id: number;
      upload_url: string;
      upload_headers: Record<string, string>;
    }>("/files", { filename: file.name, mime, size: file.size, purpose: "submission" });
    await axios.put(ticket.upload_url, file, { headers: ticket.upload_headers });
    await api.post(`/files/${ticket.id}/complete`);
    return ticket.id;
  },
  async getStepQuestions(stepId: number): Promise<StudentQuestion[]> {
    return (await api.get<StudentQuestion[]>(`/steps/${stepId}/questions`)).data;
  },

  async askQuestion(stepId: number, text: string): Promise<StudentQuestion> {
    return (await api.post<StudentQuestion>(`/steps/${stepId}/questions`, { text })).data;
  },
};

// Compatibility exports for existing step components.
export const listCourses = studentCourseApi.listCourses;
export const getCourse = studentCourseApi.getCourse;
export const getStep = studentCourseApi.getStep;
export const getSubmissions = studentCourseApi.getSubmissions;
export const getSubmission = studentCourseApi.getSubmission;
export const submitAnswer = studentCourseApi.submitAnswer;
export const getAnswer = studentCourseApi.getAnswer;
export const getContentFileUrl = studentCourseApi.getContentFileUrl;
export const uploadSubmissionFile = studentCourseApi.uploadSubmissionFile;
export const getStepQuestions = studentCourseApi.getStepQuestions;
export const askQuestion = studentCourseApi.askQuestion;
