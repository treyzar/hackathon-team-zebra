<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { UserRole } from "@/api/http";
import BrandMark from "./BrandMark.vue";
import { isNavigationItemActive, navigationForRole } from "./items";

const props = defineProps<{
  role: UserRole | null;
  username: string;
  menuOpen: boolean;
}>();

const emit = defineEmits<{ openMenu: []; logout: [] }>();

const route = useRoute();
const items = computed(() => navigationForRole(props.role));
</script>

<template>
  <header class="top-navigation">
    <button
      class="top-menu-button"
      type="button"
      aria-label="Открыть меню"
      aria-controls="app-navigation"
      :aria-expanded="menuOpen"
      @click="emit('openMenu')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
    </button>
    <div class="top-brand">
      <BrandMark />
      <strong>Код роста</strong>
    </div>
    <nav class="top-links" aria-label="Разделы">
      <RouterLink
        v-for="item in items"
        :key="item.path"
        :to="item.path"
        class="top-link"
        :class="{ 'top-link--active': isNavigationItemActive(item, route.path) }"
        :aria-current="isNavigationItemActive(item, route.path) ? 'page' : undefined"
      >
        {{ item.label }}
      </RouterLink>
    </nav>
    <div class="top-account">
      <span class="top-username">{{ username }}</span>
      <button class="top-logout" type="button" @click="emit('logout')">Выйти</button>
    </div>
  </header>
</template>

<style scoped>
.top-navigation {
  display: flex;
  align-items: center;
  gap: 32px;
  min-height: 72px;
  padding: 12px 48px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  font-size: 16px;
}
.top-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 800;
  white-space: nowrap;
}
.top-links {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.top-link {
  padding: 8px 12px;
  border-radius: var(--radius-field);
  color: var(--color-muted);
  text-decoration: none;
  white-space: nowrap;
}
.top-link:hover {
  background: var(--color-bg);
  color: var(--color-text);
}
.top-link--active,
.top-link--active:hover {
  background: transparent;
  color: var(--color-primary);
  font-weight: 600;
}
.top-account {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 15px;
}
.top-username {
  max-width: 180px;
  overflow: hidden;
  color: var(--color-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.top-logout {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  cursor: pointer;
}
.top-logout:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}
.top-menu-button {
  display: none;
  width: 44px;
  height: 44px;
  flex: none;
  place-items: center;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
}
.top-menu-button svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
}
@media (max-width: 1100px) {
  .top-navigation {
    gap: 20px;
    padding-right: 24px;
    padding-left: 24px;
  }
}
@media (max-width: 860px) {
  .top-navigation {
    gap: 12px;
    padding: 12px 16px;
  }
  .top-menu-button {
    display: grid;
  }
  .top-links,
  .top-account {
    display: none;
  }
}
</style>
