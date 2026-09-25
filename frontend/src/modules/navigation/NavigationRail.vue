<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { UserRole } from "@/api/http";
import NavigationIcon from "./NavigationIcon.vue";
import NotificationBell from "@/modules/notifications/NotificationBell.vue";
import { isNavigationItemActive, navigationForRole } from "./items";

const props = defineProps<{
  role: UserRole | null;
  username: string;
  menuOpen: boolean;
  /** Bigger touch targets for young students. */
  large?: boolean;
}>();

const emit = defineEmits<{ openMenu: [] }>();

const route = useRoute();
const items = computed(() => navigationForRole(props.role));
</script>

<template>
  <aside class="navigation-rail" :class="{ 'navigation-rail--large': large }" aria-label="Разделы">
    <button
      class="rail-button"
      type="button"
      aria-label="Открыть меню"
      aria-controls="app-navigation"
      :aria-expanded="menuOpen"
      @click="emit('openMenu')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
    </button>
    <span class="rail-divider" aria-hidden="true" />
    <RouterLink
      v-for="item in items"
      :key="item.path"
      :to="item.path"
      class="rail-button"
      :class="{ 'rail-button--active': isNavigationItemActive(item, route.path) }"
      :aria-current="isNavigationItemActive(item, route.path) ? 'page' : undefined"
      :aria-label="item.label"
      :title="item.label"
    >
      <NavigationIcon :name="item.icon" />
    </RouterLink>
    <span class="rail-spacer" />
    <NotificationBell variant="rail" class="rail-bell"/>
    <span class="rail-avatar" :title="username">{{ username.slice(0, 1).toUpperCase() }}</span>
  </aside>
</template>

<style scoped>
.navigation-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 72px;
  height: 100%;
  padding: 14px 0;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
}
.rail-button {
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
  text-decoration: none;
}
.rail-button:hover {
  background: var(--color-bg);
  color: var(--color-text);
}
.rail-button--active,
.rail-button--active:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.rail-button svg {
  width: 24px;
  height: 24px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}
.rail-divider {
  width: 40px;
  height: 1px;
  margin: 6px 0;
  background: var(--color-border);
}
.rail-spacer {
  flex: 1;
}
.navigation-rail--large {
  gap: 8px;
  width: 80px;
}
.navigation-rail--large .rail-button {
  width: 56px;
  height: 56px;
  border-radius: 14px;
}
.navigation-rail--large .rail-button svg,
.navigation-rail--large .rail-button :deep(.navigation-icon) {
  width: 26px;
  height: 26px;
}
.navigation-rail--large .rail-divider {
  width: 44px;
  margin: 4px 0;
}
.navigation-rail--large .rail-avatar {
  width: 48px;
  height: 48px;
  background: var(--color-primary);
  font-size: 15px;
}
.rail-avatar {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 50%;
  background: var(--color-ink);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.rail-bell {
  margin-bottom: 4px;
}
.rail-bell :deep(.notifications-bell--rail) {
  border-radius: var(--radius-control);
  color: var(--color-muted);
}
.rail-bell :deep(.notifications-bell--rail:hover) {
  background: var(--color-bg);
  color: var(--color-text);
}
.rail-bell :deep(.notifications-bell--rail[aria-expanded="true"]) {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.rail-bell :deep(.notifications-bell-dot) {
  top: 8px;
  right: 8px;
}
</style>
