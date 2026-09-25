<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { getApiErrorMessage } from "@/api/errors";
import { useAuthStore } from "@/stores/auth";
import { useNotificationsStore } from "@/stores/notifications";
import { formatRelative, viewNotification } from "./presentation";

const props = withDefaults(
  defineProps<{
    variant?: "icon" | "sidebar";
  }>(),
  { variant: "icon" },
);

const auth = useAuthStore();
const store = useNotificationsStore();
const router = useRouter();

const open = ref(false);
const root = ref<HTMLElement | null>(null);
const error = ref("");

function toggle(): void {
  open.value = !open.value;
  if (open.value && !store.loaded) {
    void store.load().catch((cause) => {
      error.value = getApiErrorMessage(cause);
    });
  }
}

function close(): void {
  open.value = false;
  error.value = "";
}

function onDocClick(event: MouseEvent): void {
  if (!open.value) return;
  if (root.value && !root.value.contains(event.target as Node)) close();
}

function onKey(event: KeyboardEvent): void {
  if (event.key === "Escape") close();
}

async function activate(
  id: number,
  target: ReturnType<typeof viewNotification>["to"],
): Promise<void> {
  try {
    await store.markRead(id);
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  }
  if (target) {
    close();
    await router.push(target);
  }
}

async function markAll(): Promise<void> {
  try {
    await store.markAllRead();
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  }
}

onMounted(() => {
  store.startPolling();
  document.addEventListener("mousedown", onDocClick);
  document.addEventListener("keydown", onKey);
});
onBeforeUnmount(() => {
  store.stopPolling();
  document.removeEventListener("mousedown", onDocClick);
  document.removeEventListener("keydown", onKey);
});

watch(
  () => store.loaded,
  (v) => {
    if (v) error.value = "";
  },
);
</script>

<template>
  <div
    ref="root"
    class="notifications-bell-wrap"
    :class="`notifications-bell-wrap--${props.variant}`"
  >
    <button
      class="notifications-bell"
      :class="`notifications-bell--${props.variant}`"
      type="button"
      :aria-expanded="open"
      :aria-label="
        store.hasUnread
          ? `Уведомления, непрочитанных: ${store.unread}`
          : 'Уведомления'
      "
      @click="toggle"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 8a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
        <path d="M10 18a2 2 0 0 0 4 0" />
      </svg>
      <span v-if="props.variant === 'sidebar'" class="notifications-bell-label">
        Уведомления
      </span>
      <span v-if="store.hasUnread" class="notifications-bell-badge">
        {{ store.unread > 99 ? "99+" : store.unread }}
      </span>
    </button>

    <div
      v-if="open"
      class="notifications-popover"
      role="dialog"
      aria-label="Уведомления"
    >
      <header class="notifications-popover-head">
        <strong>Уведомления</strong>
        <button
          v-if="store.hasUnread"
          class="notifications-popover-action"
          type="button"
          @click="markAll"
        >
          Прочитать все
        </button>
      </header>

      <p v-if="error" class="admin-error" role="alert">{{ error }}</p>

      <div v-if="store.loading && !store.loaded" class="notifications-popover-empty">
        Загружаем…
      </div>
      <div v-else-if="!store.items.length" class="notifications-popover-empty">
        Пока пусто
      </div>

      <ul v-else class="notifications-popover-list">
        <li
          v-for="item in store.items.slice(0, 20)"
          :key="item.id"
          class="notifications-popover-item"
          :class="[
            `notifications-popover-item--${viewNotification(item, auth.role).tone}`,
            { 'notifications-popover-item--unread': item.read_at === null },
          ]"
        >
          <button
            type="button"
            class="notifications-popover-link"
            @click="activate(item.id, viewNotification(item, auth.role).to)"
          >
            <div class="notifications-popover-body">
              <strong>{{ viewNotification(item, auth.role).title }}</strong>
              <span>{{ viewNotification(item, auth.role).description }}</span>
            </div>
            <span class="notifications-popover-time">
              {{ formatRelative(item.created_at) }}
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.notifications-bell-wrap {
  position: relative;
  flex: none;
}

/* Иконка-вариант: квадратная кнопка как раньше */
.notifications-bell--icon {
  position: relative;
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
}
.notifications-bell--icon:hover {
  border-color: var(--color-primary-pale);
  color: var(--color-primary);
}

/* Sidebar-вариант: выглядит как пункт меню рядом с RouterLink'ами */
.notifications-bell-wrap--sidebar {
  width: 100%;
}
.notifications-bell--sidebar {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 44px;
  padding: 0 12px;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text);
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
}
.notifications-bell--sidebar:hover {
  background: var(--color-bg);
}
.notifications-bell--sidebar[aria-expanded="true"] {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.notifications-bell--sidebar[aria-expanded="true"] svg {
  color: var(--color-primary);
}

.notifications-bell svg {
  width: 22px;
  height: 22px;
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.notifications-bell--icon svg {
  width: 22px;
  height: 22px;
}
.notifications-bell-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notifications-bell-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--color-primary);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 20px;
  text-align: center;
}
/* В sidebar-варианте бейдж — часть flex-строки, не абсолютный */
.notifications-bell--sidebar .notifications-bell-badge {
  position: static;
  flex: none;
}

.notifications-popover {
  position: absolute;
  z-index: 40;
  width: min(420px, calc(100vw - 32px));
  max-height: min(560px, 70vh);
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: 0 18px 48px rgba(11, 18, 32, 0.16);
  overflow: hidden;
}

/* Иконка: как было — снизу от кнопки */
.notifications-bell-wrap--icon .notifications-popover {
  top: calc(100% + 8px);
  right: 0;
  bottom: auto;
  left: auto;
}

/* Sidebar: открывается ВБОК, а не вниз — тогда ничего не уезжает за экран */
.notifications-bell-wrap--sidebar .notifications-popover {
  top: auto;
  bottom: 0;
  left: calc(100% + 8px);
  right: auto;
}

.notifications-popover-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}
.notifications-popover-head strong {
  font-size: 14px;
}
.notifications-popover-action {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.notifications-popover-action:hover {
  text-decoration: underline;
}
.notifications-popover-empty {
  padding: 24px 16px;
  color: var(--color-muted);
  font-size: 13px;
  text-align: center;
}
.notifications-popover-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  min-height: 0;
}
.notifications-popover-item + .notifications-popover-item {
  border-top: 1px solid var(--color-border);
}
.notifications-popover-item--unread {
  background: var(--color-primary-soft);
}
.notifications-popover-item--success .notifications-popover-body strong {
  color: #168054;
}
.notifications-popover-item--warning .notifications-popover-body strong {
  color: #a05c16;
}
.notifications-popover-item--error .notifications-popover-body strong {
  color: #a53b3b;
}
.notifications-popover-link {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 11px 16px;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.notifications-popover-link:hover {
  background: var(--color-bg);
}
.notifications-popover-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
.notifications-popover-body strong {
  font-size: 13px;
  color: var(--color-text);
}
.notifications-popover-body span {
  color: var(--color-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.notifications-popover-time {
  color: var(--color-subtle);
  font-size: 11px;
  white-space: nowrap;
  padding-top: 2px;
}
</style>