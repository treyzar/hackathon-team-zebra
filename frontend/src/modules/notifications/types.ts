export type NotificationTone = "success" | "error" | "warning" | "info";

export interface AppNotification {
  id: number;
  tone: NotificationTone;
  title?: string;
  message: string;
  duration: number | null;
}

export interface NotifyOptions {
  tone?: NotificationTone;
  title?: string;
  duration?: number | null;
}
