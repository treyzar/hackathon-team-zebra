import { readonly, ref } from "vue";
import type { AppNotification, NotifyOptions } from "./types";

const DEFAULT_DURATION = 10_000;
const notifications = ref<AppNotification[]>([]);
const timers = new Map<number, ReturnType<typeof setTimeout>>();
let nextId = 1;

function dismiss(id: number): void {
  const timer = timers.get(id);
  if (timer) {
    clearTimeout(timer);
    timers.delete(id);
  }

  notifications.value = notifications.value.filter((notification) => notification.id !== id);
}

function notify(message: string, options: NotifyOptions = {}): number {
  const id = nextId++;
  const duration = options.duration === undefined ? DEFAULT_DURATION : options.duration;

  notifications.value.push({
    id,
    tone: options.tone ?? "info",
    title: options.title,
    message,
    duration,
  });

  if (duration !== null && duration > 0) {
    timers.set(
      id,
      setTimeout(() => dismiss(id), duration),
    );
  }

  return id;
}

function success(message: string, options: Omit<NotifyOptions, "tone"> = {}): number {
  return notify(message, { ...options, tone: "success" });
}

function error(message: string, options: Omit<NotifyOptions, "tone"> = {}): number {
  return notify(message, { ...options, tone: "error" });
}

function warning(message: string, options: Omit<NotifyOptions, "tone"> = {}): number {
  return notify(message, { ...options, tone: "warning" });
}

function info(message: string, options: Omit<NotifyOptions, "tone"> = {}): number {
  return notify(message, { ...options, tone: "info" });
}

function clear(): void {
  for (const timer of timers.values()) clearTimeout(timer);
  timers.clear();
  notifications.value = [];
}

export function useNotifications() {
  return {
    notifications: readonly(notifications),
    notify,
    success,
    error,
    warning,
    info,
    dismiss,
    clear,
  };
}
