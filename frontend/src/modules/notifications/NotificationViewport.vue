<script setup lang="ts">
import { useNotifications } from "./useNotifications";
import type { NotificationTone } from "./types";

const { notifications, dismiss } = useNotifications();

const defaultTitles: Record<NotificationTone, string> = {
  success: "Готово",
  error: "Не удалось выполнить действие",
  warning: "Обратите внимание",
  info: "Информация",
};
</script>

<template>
  <Teleport to="body">
    <div class="notification-viewport" aria-live="polite" aria-relevant="additions removals">
      <TransitionGroup name="notification-list">
        <article
          v-for="notification in notifications"
          :key="notification.id"
          class="notification-toast"
          :class="`notification-toast--${notification.tone}`"
          :role="notification.tone === 'error' ? 'alert' : 'status'"
        >
          <div class="notification-toast__body">
            <strong>{{ notification.title ?? defaultTitles[notification.tone] }}</strong>
            <span>{{ notification.message }}</span>
          </div>
          <button
            class="notification-toast__close"
            type="button"
            aria-label="Закрыть уведомление"
            @click="dismiss(notification.id)"
          >
            ×
          </button>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.notification-viewport {
  position: fixed;
  z-index: 2000;
  right: 24px;
  bottom: 24px;
  width: min(420px, calc(100vw - 32px));
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}
.notification-toast {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 14px 14px 16px;
  border: 1px solid #e1e6f0;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 16px 40px rgba(29, 43, 67, 0.16);
  pointer-events: auto;
}
.notification-toast--error {
  border-color: #f2c5c1;
  background: #fff7f6;
}
.notification-toast--success {
  border-color: #cce9da;
  background: #f5fcf8;
}
.notification-toast--warning {
  border-color: #f1d6a7;
  background: #fffaf1;
}
.notification-toast--info {
  border-color: #cbd8fb;
  background: #f7f9ff;
}
.notification-toast__body {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.notification-toast__body strong {
  color: #1d2b43;
  font-size: 14px;
}
.notification-toast__body span {
  color: #4a546b;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.notification-toast__close {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #6e788d;
  font:
    500 22px/1 system-ui,
    sans-serif;
  cursor: pointer;
}
.notification-toast__close:hover {
  background: rgba(29, 43, 67, 0.07);
  color: #1d2b43;
}
.notification-list-enter-active,
.notification-list-leave-active,
.notification-list-move {
  transition:
    opacity 180ms ease,
    transform 180ms ease;
}
.notification-list-enter-from,
.notification-list-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
@media (max-width: 560px) {
  .notification-viewport {
    right: 16px;
    bottom: 16px;
  }
}
</style>
