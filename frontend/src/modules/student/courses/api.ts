import axios from "axios";
import { api } from "@/api/http";
import type { Course, CourseListItem, StudentStep, Submission } from "./types";

export async function listCourses(): Promise<CourseListItem[]> {
  return (await api.get<CourseListItem[]>("/courses")).data;
}

export async function getCourse(id: number): Promise<Course> {
  return (await api.get<Course>(`/courses/${id}`)).data;
}

export async function getStep(id: number): Promise<StudentStep> {
  return (await api.get<StudentStep>(`/steps/${id}`)).data;
}

export async function getSubmissions(id: number): Promise<Submission[]> {
  return (await api.get<Submission[]>(`/steps/${id}/submissions`)).data;
}

export async function getSubmission(id: number): Promise<Submission> {
  return (await api.get<Submission>(`/submissions/${id}`)).data;
}

export async function submitAnswer(
  id: number,
  answer: Record<string, unknown>,
): Promise<Submission> {
  return (await api.post<Submission>(`/steps/${id}/submissions`, { answer })).data;
}

export async function getAnswer(id: number): Promise<Record<string, unknown>> {
  return (await api.get<Record<string, unknown>>(`/steps/${id}/answer`)).data;
}

export async function getContentFileUrl(id: number): Promise<string> {
  return (await api.get<{ download_url: string }>(`/files/${id}`)).data.download_url;
}

export async function uploadSubmissionFile(file: File): Promise<number> {
  const mime = file.type || "application/octet-stream";
  const { data: ticket } = await api.post<{
    id: number;
    upload_url: string;
    upload_headers: Record<string, string>;
  }>("/files", { filename: file.name, mime, size: file.size, purpose: "submission" });
  await axios.put(ticket.upload_url, file, { headers: ticket.upload_headers });
  await api.post(`/files/${ticket.id}/complete`);
  return ticket.id;
}
