import axios from "axios";
import { api } from "@/api/http";

interface UploadTicket {
  id: number;
  upload_url: string;
  upload_headers: Record<string, string>;
}

export async function fileUrl(id: number): Promise<string> {
  const response = await api.get<{ download_url: string }>(`/files/${id}`);
  return response.data.download_url;
}

async function uploadFile(file: File, purpose: "content" | "answer_key"): Promise<number> {
  const ticket = (
    await api.post<UploadTicket>("/files", {
      filename: file.name,
      mime: file.type || "application/octet-stream",
      size: file.size,
      purpose,
    })
  ).data;
  await axios.put(ticket.upload_url, file, { headers: ticket.upload_headers });
  await api.post(`/files/${ticket.id}/complete`);
  return ticket.id;
}

export async function uploadContentImage(file: File): Promise<{ id: number; url: string }> {
  if (!file.type.startsWith("image/")) throw new Error("Выберите файл изображения.");
  const id = await uploadFile(file, "content");
  return { id, url: await fileUrl(id) };
}

export async function uploadAnswerFile(file: File): Promise<number> {
  return uploadFile(file, "answer_key");
}
