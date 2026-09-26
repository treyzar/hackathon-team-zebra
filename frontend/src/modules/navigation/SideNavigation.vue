<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { UserRole } from "@/api/http";
import BrandMark from "./BrandMark.vue";
import NavigationIcon from "./NavigationIcon.vue";
import NotificationBell from "@/modules/notifications/NotificationBell.vue";
import { isNavigationItemActive, navigationForRole, roleLabel } from "./items";

const props = defineProps<{
  role: UserRole | null;
  username: string;
  /** Drawer mode: floats over the page and closes on Escape. */
  overlay?: boolean;
  /** Bigger type and touch targets for young students. */
  large?: boolean;
}>();

const emit = defineEmits<{
  navigate: [];
  close: [];
  logout: [];
}>();

const route = useRoute();
const items = computed(() => navigationForRole(props.role));
const root = ref<HTMLElement | null>(null);

onMounted(async () => {
  if (!props.overlay) return;
  // Move focus into the drawer so keyboard users land inside the menu they opened.
  await nextTick();
  root.value?.querySelector<HTMLElement>("a, button")?.focus();
});
</script>

<template>
  <nav
    id="app-navigation"
    ref="root"
    class="side-navigation"
    :class="{ 'side-navigation--overlay': overlay, 'side-navigation--large': large }"
    aria-label="Основная навигация"
    @keydown.esc="emit('close')"
  >
    <div class="side-brand">
      <button
        v-if="overlay"
        class="side-close"
        type="button"
        aria-label="Закрыть меню"
        @click="emit('close')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
      </button>
      <BrandMark v-else @click="emit('navigate')" />
      <div class="side-brand-copy">
        <strong>Код роста</strong>
        <span>Платформа обучения</span>
      </div>
    </div>

    <div class="side-links">
      <RouterLink
        v-for="item in items"
        :key="item.path"
        :to="item.path"
        class="side-link"
        :class="{ 'side-link--active': isNavigationItemActive(item, route.path) }"
        :aria-current="isNavigationItemActive(item, route.path) ? 'page' : undefined"
        @click="emit('navigate')"
      >
        <NavigationIcon :name="item.icon" />
        <span>{{ item.label }}</span>
      </RouterLink>
      <slot />
    </div>
    <NotificationBell variant="sidebar" class="side-bell" />
    <div class="side-account">
      <span class="side-avatar" aria-hidden="true">{{ username.slice(0, 1).toUpperCase() }}</span>
      <span class="side-account-copy">
        <strong>{{ username }}</strong>
        <span>{{ roleLabel(role) }}</span>
      </span>
      <button class="side-logout" type="button" @click="emit('logout')">Выйти</button>
    </div>
  </nav>
</template>

<style scoped>
.side-navigation {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 240px;
  height: 100%;
  min-height: 0;
  padding: 14px 12px;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: max(14px, var(--font-size-floor, 0px));
}
.side-navigation--overlay {
  position: fixed;
  z-index: 40;
  top: 0;
  left: 0;
  width: 290px;
  max-width: calc(100vw - 24px);
  height: 100dvh;
  border-right: 0;
  box-shadow: 8px 0 32px #0b12202e;
}
.side-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 0 12px;
}
.side-brand-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.25;
}
.side-brand-copy strong {
  font-size: 15px;
}
.side-brand-copy span {
  color: var(--color-muted);
  font-size: max(12px, var(--font-size-floor, 0px));
}
.side-close {
  display: grid;
  width: 48px;
  height: 48px;
  flex: none;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
}
.side-close:hover {
  background: var(--color-bg);
  color: var(--color-text);
}
.side-close svg {
  width: 24px;
  height: 24px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}
.side-links {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-height: 0;
  overflow-y: auto;
}

.side-link {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 0 12px;
  border-radius: var(--radius-control);
  color: var(--color-text);
  font-weight: 500;
  text-decoration: none;
}
.side-link:hover {
  background: var(--color-bg);
  color: var(--color-text);
}
.side-link :deep(.navigation-icon) {
  flex: none;
  color: var(--color-muted);
}
.side-link--active,
.side-link--active:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}
.side-link--active :deep(.navigation-icon) {
  color: var(--color-primary);
}

.side-bell {
  margin-top: 4px;
  margin-bottom: 4px;
}

.side-bell :deep(.notifications-bell--sidebar) {
  color: var(--color-text);
  font-weight: 500;
}
.side-bell :deep(.notifications-bell--sidebar svg) {
  color: var(--color-muted);
}
.side-bell :deep(.notifications-bell--sidebar:hover) {
  background: var(--color-bg);
  color: var(--color-text);
}
.side-bell :deep(.notifications-bell--sidebar[aria-expanded="true"]) {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}
.side-bell :deep(.notifications-bell--sidebar[aria-expanded="true"] svg) {
  color: var(--color-primary);
}

.side-navigation--large .side-bell :deep(.notifications-bell--sidebar) {
  gap: 14px;
  min-height: var(--button-height);
  padding: 0 14px;
  border-radius: 14px;
  font-size: 18px;
}
.side-navigation--large .side-bell :deep(.notifications-bell--sidebar svg) {
  width: 26px;
  height: 26px;
}
.side-navigation--large .side-bell :deep(.notifications-bell-dot) {
  width: 12px;
  height: 12px;
}

.side-account {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px 0;
  border-top: 1px solid var(--color-border);
}
.side-avatar {
  display: grid;
  width: 36px;
  height: 36px;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: var(--color-ink);
  color: #fff;
  font-size: max(13px, var(--font-size-floor, 0px));
  font-weight: 700;
}
.side-account-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  line-height: 1.3;
}
.side-account-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-account-copy span {
  color: var(--color-muted);
  font-size: max(12px, var(--font-size-floor, 0px));
}
.side-logout {
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-size: max(13px, var(--font-size-floor, 0px));
  cursor: pointer;
}
.side-navigation--large {
  width: 320px;
  gap: 6px;
  padding: 14px;
  font-size: 18px;
}
.side-navigation--large .side-link {
  gap: 14px;
  min-height: var(--button-height);
  padding: 0 14px;
  border-radius: 14px;
}
.side-navigation--large .side-link :deep(.navigation-icon) {
  width: 26px;
  height: 26px;
}
.side-navigation--large .side-close {
  width: 56px;
  height: 56px;
  border-radius: 14px;
}
.side-navigation--large .side-avatar {
  width: 44px;
  height: 44px;
  background: var(--color-primary);
  font-size: 15px;
}
.side-navigation--large .side-account-copy span,
.side-navigation--large .side-logout {
  font-size: 15px;
}
.side-navigation--large .side-logout {
  min-height: var(--button-height);
  padding: 0 8px;
}
.side-logout:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}
</style>
