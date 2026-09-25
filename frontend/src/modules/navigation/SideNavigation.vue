<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { UserRole } from "@/api/http";
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
import NavigationIcon from "./NavigationIcon.vue";
import { navigationForRole } from "./items";

const props = defineProps<{
  role: UserRole | null;
  username: string;
  collapsed: boolean;
  mobileOpen: boolean;
}>();

const emit = defineEmits<{
  toggleCollapse: [];
  navigate: [];
  logout: [];
}>();

const items = computed(() => navigationForRole(props.role));
const route = useRoute();
const roleLabel = computed(() => {
  if (props.role === "student") return "Ученик";
  if (props.role === "curator") return "Куратор";
  return "Администратор";
});
</script>

<template>
  <aside
    id="app-navigation"
    class="side-navigation"
    :class="{ 'side-navigation--collapsed': collapsed, 'side-navigation--open': mobileOpen }"
    aria-label="Основная навигация"
  >
    <div class="navigation-brand">
      <RouterLink
        class="brand-mark"
        :to="DASHBOARD_ROUTE.path"
        aria-label="Код роста — главная"
        @click="emit('navigate')"
      >
        <span aria-hidden="true">&lt;/&gt;</span>
      </RouterLink>
      <div v-if="!collapsed" class="brand-copy">
        <strong>Код роста</strong>
        <span>Платформа обучения</span>
      </div>
    </div>

    <div class="navigation-main">
      <p v-if="!collapsed" class="navigation-caption">РАБОЧЕЕ ПРОСТРАНСТВО</p>
      <nav class="navigation-links" aria-label="Разделы">
        <RouterLink
          v-for="item in items"
          :key="item.path"
          :to="item.path"
          class="navigation-link"
          :class="{ 'navigation-link--active': route.path.startsWith(item.path + '/') }"
          :aria-current="route.path.startsWith(item.path + '/') ? 'page' : undefined"
          :aria-label="collapsed ? item.label : undefined"
          :title="collapsed ? item.label : undefined"
          @click="emit('navigate')"
        >
          <NavigationIcon :name="item.icon" />
          <span v-if="!collapsed" class="navigation-link-label">{{ item.label }}</span>
        </RouterLink>
      </nav>
    </div>

    <div class="navigation-bottom">
      <button
        class="navigation-collapse"
        type="button"
        :aria-label="collapsed ? 'Развернуть навигацию' : 'Свернуть навигацию'"
        :title="collapsed ? 'Развернуть навигацию' : 'Свернуть навигацию'"
        @click="emit('toggleCollapse')"
      >
        <svg
          class="collapse-icon"
          :class="{ 'collapse-icon--reversed': collapsed }"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="m14 6-6 6 6 6" />
        </svg>
        <span v-if="!collapsed">Свернуть меню</span>
      </button>

      <div class="navigation-account">
        <span class="account-avatar" aria-hidden="true">{{
          username.slice(0, 1).toUpperCase()
        }}</span>
        <div v-if="!collapsed" class="account-copy">
          <strong>{{ username }}</strong>
          <span>{{ roleLabel }}</span>
        </div>
        <button
          class="account-logout"
          type="button"
          aria-label="Выйти из аккаунта"
          title="Выйти"
          @click="emit('logout')"
        >
          <svg
            width="19"
            height="19"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5M14 16l4-4-4-4m4 4H9" />
          </svg>
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.side-navigation {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 28px 18px 22px;
  color: #c3cce0;
}
.navigation-brand {
  display: flex;
  align-items: center;
  gap: 13px;
  min-height: 52px;
  padding: 0 10px;
}
.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  flex: none;
  place-items: center;
  border-radius: 13px;
  background: #3457f0;
  color: white;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.08em;
  box-shadow: 0 8px 22px #15297660;
}
.brand-mark:focus-visible,
.navigation-link:focus-visible,
.navigation-collapse:focus-visible,
.account-logout:focus-visible {
  outline: 3px solid #a5b7ff;
  outline-offset: 3px;
}
.brand-copy,
.account-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.brand-copy strong {
  color: #fff;
  font-size: 17px;
  line-height: 1.2;
  white-space: nowrap;
}
.brand-copy span {
  margin-top: 4px;
  color: #8794af;
  font-size: 11px;
  white-space: nowrap;
}
.navigation-main {
  flex: 1;
  min-height: 0;
  margin-top: 54px;
  overflow-y: auto;
  overscroll-behavior-y: contain;
}
.navigation-caption {
  margin: 0 10px 15px;
  color: #72809c;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.16em;
  white-space: nowrap;
}
.navigation-links {
  display: grid;
  gap: 6px;
}
.navigation-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 48px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 12px;
  color: #9ba9c3;
  text-decoration: none;
  transition:
    background 0.18s,
    color 0.18s,
    border-color 0.18s;
}
.navigation-link:hover {
  background: #18243c;
  color: #fff;
}
.navigation-link.router-link-exact-active,
.navigation-link--active {
  border-color: #5472fb4f;
  background: #3457f0;
  color: #fff;
  box-shadow: 0 8px 20px #06102459;
}
.navigation-link-label {
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.navigation-icon {
  flex: none;
}
.navigation-bottom {
  display: grid;
  gap: 15px;
}
.navigation-collapse {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid #24324b;
  border-radius: 11px;
  background: #0c1628;
  color: #a4b0c8;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  text-align: left;
}
.navigation-collapse:hover {
  border-color: #4b5b7c;
  color: #fff;
}
.collapse-icon {
  flex: none;
  transition: transform 0.2s;
}
.collapse-icon--reversed {
  transform: rotate(180deg);
}
.navigation-account {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 64px;
  padding: 9px 8px;
  border-top: 1px solid #24324b;
}
.account-avatar {
  display: grid;
  width: 37px;
  height: 37px;
  flex: none;
  place-items: center;
  border-radius: 11px;
  background: #243354;
  color: #e2e8ff;
  font-size: 15px;
  font-weight: 700;
}
.account-copy {
  flex: 1;
}
.account-copy strong {
  overflow: hidden;
  color: #f2f5ff;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.account-copy span {
  margin-top: 3px;
  color: #8391ad;
  font-size: 11px;
}
.account-logout {
  display: grid;
  width: 31px;
  height: 31px;
  flex: none;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #8391ad;
  cursor: pointer;
}
.account-logout:hover {
  background: #24324b;
  color: #fff;
}
.side-navigation--collapsed {
  align-items: center;
  padding-right: 11px;
  padding-left: 11px;
}
.side-navigation--collapsed .navigation-brand {
  padding: 0;
}
.side-navigation--collapsed .navigation-main,
.side-navigation--collapsed .navigation-links,
.side-navigation--collapsed .navigation-bottom {
  width: 100%;
}
.side-navigation--collapsed .navigation-main {
  margin-top: 54px;
}
.side-navigation--collapsed .navigation-link,
.side-navigation--collapsed .navigation-collapse {
  justify-content: center;
  padding-right: 0;
  padding-left: 0;
}
.side-navigation--collapsed .navigation-account {
  flex-direction: column;
  padding-right: 0;
  padding-left: 0;
}
@media (max-width: 767px) {
  .side-navigation {
    position: fixed;
    z-index: 30;
    top: 0;
    bottom: 0;
    left: 0;
    width: 265px;
    background: #0b1220;
    box-shadow: 22px 0 60px #06102470;
    transform: translateX(-105%);
    transition: transform 0.22s ease;
  }
  .side-navigation--open {
    transform: translateX(0);
  }
  .side-navigation--collapsed {
    align-items: stretch;
    padding-right: 18px;
    padding-left: 18px;
  }
  .side-navigation--collapsed .navigation-brand {
    padding: 0 10px;
  }
  .side-navigation--collapsed .navigation-link,
  .side-navigation--collapsed .navigation-collapse {
    justify-content: flex-start;
    padding: 0 14px;
  }
  .side-navigation--collapsed .navigation-account {
    flex-direction: row;
    padding: 9px 8px;
  }
  .navigation-collapse {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .navigation-link,
  .collapse-icon,
  .side-navigation {
    transition: none;
  }
}
</style>
