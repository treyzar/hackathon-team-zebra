import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { notificationsApi, type Notification } from "@/modules/notifications/api";

const POLL_INTERVAL_MS = 30_000;

export const useNotificationsStore = defineStore("notifications", () => {
  const unread = ref(0);
  const items = ref<Notification[]>([]);
  const loading = ref(false);
  const loaded = ref(false);

  let timer: ReturnType<typeof setInterval> | null = null;
  let unreadPromise: Promise<void> | null = null;

  const hasUnread = computed(() => unread.value > 0);

  async function refreshUnread(): Promise<void> {
    if (unreadPromise) return unreadPromise;
    unreadPromise = notificationsApi
      .unreadCount()
      .then((count) => {
        unread.value = count;
      })
      .catch(() => {
        /* :( */
      })
      .finally(() => {
        unreadPromise = null;
      });
    return unreadPromise;
  }

  async function load(): Promise<void> {
    loading.value = true;
    try {
      items.value = await notificationsApi.list({ limit: 100 });
      unread.value = items.value.filter((n) => n.read_at === null).length;
      loaded.value = true;
    } finally {
      loading.value = false;
    }
  }

  async function markRead(id: number): Promise<void> {
    const target = items.value.find((n) => n.id === id);
    if (!target || target.read_at !== null) return;
    const updated = await notificationsApi.markRead(id);
    items.value = items.value.map((n) => (n.id === id ? updated : n));
    unread.value = Math.max(0, unread.value - 1);
  }

  async function markAllRead(): Promise<void> {
    await notificationsApi.markAllRead();
    const now = new Date().toISOString();
    items.value = items.value.map((n) => (n.read_at ? n : { ...n, read_at: now }));
    unread.value = 0;
  }

  function startPolling(): void {
    void refreshUnread();
    if (timer) return;
    timer = setInterval(() => void refreshUnread(), POLL_INTERVAL_MS);
  }

  function stopPolling(): void {
    if (timer) clearInterval(timer);
    timer = null;
  }

  return {
    unread,
    hasUnread,
    items,
    loading,
    loaded,
    refreshUnread,
    load,
    markRead,
    markAllRead,
    startPolling,
    stopPolling,
  };
});