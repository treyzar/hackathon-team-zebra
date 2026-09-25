<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { UserRole } from "@/api/http";
import NavigationIcon from "./NavigationIcon.vue";
import { isNavigationItemActive, navigationForRole } from "./items";

const props = defineProps<{
  role: UserRole | null;
  username: string;
  menuOpen: boolean;
}>();

const emit = defineEmits<{ openMenu: [] }>();

const route = useRoute();
const items = computed(() => navigationForRole(props.role));
</script>

<template>
  <aside class="navigation-rail" aria-label="Разделы">
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
</style>
