import { api } from "@/api/http";

export type NotificationType =
  | "deadline_approaching"
  | "deadline_passed"
  | "deadline_changed"
  | "submission_reviewed"
  | "submission_pending_review"
  | "submission_queue_reminder"
  | "question_asked"
  | "question_answered"
  | "step_solved"
  | "step_unlocked"
  | "step_breaking_change"
  | "course_completed"
  | "course_published"
  | "course_attention_needed"
  | "added_to_group"
  | "moved_to_group"
  | "assigned_group"
  | "hello"
  | "role_changed";

export type NotificationSeverity = "info" | "success" | "warning" | "error";

export interface Notification {
  id: number;
  type: NotificationType;
  severity: NotificationSeverity;
  payload: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}

interface UnreadCount {
  count: number;
}

export const notificationsApi = {
  async list(
    options: { unreadOnly?: boolean; limit?: number; offset?: number } = {},
  ): Promise<Notification[]> {
    return (
      await api.get<Notification[]>("/notifications", {
        params: {
          unread_only: options.unreadOnly ?? false,
          limit: options.limit ?? 50,
          offset: options.offset ?? 0,
        },
      })
    ).data;
  },

  async unreadCount(): Promise<number> {
    return (await api.get<UnreadCount>("/notifications/unread_count")).data.count;
  },

  async markRead(id: number): Promise<Notification> {
    return (await api.post<Notification>(`/notifications/${id}/read`)).data;
  },

  async markAllRead(): Promise<void> {
    await api.post("/notifications/read_all");
  },
};
