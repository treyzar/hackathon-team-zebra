<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { navigationForRole } from "@/modules/navigation/items";
import SideNavigation from "@/modules/navigation/SideNavigation.vue";
import { LOGIN_ROUTE } from "@/pages/login/constants";
import { useAuthStore } from "@/stores/auth";

const COLLAPSED_KEY = "zebra.navigation.collapsed";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const collapsed = ref(
  typeof window !== "undefined" && window.localStorage.getItem(COLLAPSED_KEY) === "true",
);
const mobileOpen = ref(false);
const contentBody = ref<HTMLElement | null>(null);

const homeItem = computed(() => navigationForRole(auth.role)[0]);
const pageTitle = computed(
  () => (route.meta.title as string | undefined) ?? homeItem.value?.label ?? "Главная",
);
const pageDescription = computed(
  () => (route.meta.description as string | undefined) ?? homeItem.value?.description ?? "",
);

watch(collapsed, (value) => window.localStorage.setItem(COLLAPSED_KEY, String(value)));
watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false;
    if (contentBody.value) contentBody.value.scrollTop = 0;
  },
);

async function logout(): Promise<void> {
  try {
    await auth.logout();
  } finally {
    await router.replace({ name: LOGIN_ROUTE.name });
  }
}
</script>

<template>
  <div
    class="app-shell"
    :class="{ 'app-shell--collapsed': collapsed, 'app-shell--admin': auth.role === 'admin' }"
  >
    <button
      v-if="mobileOpen"
      class="navigation-backdrop"
      type="button"
      aria-label="Закрыть меню"
      @click="mobileOpen = false"
    />

    <SideNavigation
      :role="auth.role"
      :username="auth.user?.username ?? ''"
      :collapsed="collapsed && !mobileOpen"
      :mobile-open="mobileOpen"
      @toggle-collapse="collapsed = !collapsed"
      @navigate="mobileOpen = false"
      @logout="logout"
    />

    <main class="content-island">
      <header v-if="auth.role !== 'admin'" class="content-header">
        <button
          class="mobile-menu-button"
          type="button"
          aria-label="Открыть меню"
          aria-controls="app-navigation"
          :aria-expanded="mobileOpen"
          @click="mobileOpen = true"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
        <div class="content-heading">
          <p class="content-eyebrow">КОД РОСТА <span aria-hidden="true">/</span> ЛИЧНЫЙ КАБИНЕТ</p>
          <h1>{{ pageTitle }}</h1>
          <p class="content-description">{{ pageDescription }}</p>
        </div>
        <div class="header-account" :title="auth.user?.email">
          <span class="header-account-dot" aria-hidden="true" />
          <span>{{ auth.user?.username }}</span>
        </div>
      </header>

      <header v-if="auth.role === 'admin'" class="admin-shell-header">
        <button
          class="mobile-menu-button"
          type="button"
          aria-label="Открыть меню"
          aria-controls="app-navigation"
          :aria-expanded="mobileOpen"
          @click="mobileOpen = true"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
        <div id="admin-page-header" class="admin-shell-header-content" />
        <h1 class="admin-shell-fallback">{{ pageTitle }}</h1>
      </header>

      <div
        ref="contentBody"
        class="content-body"
        role="region"
        aria-label="Содержимое страницы"
        tabindex="0"
      >
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 258px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  padding: 16px 16px 16px 0;
  background: #0b1220;
  transition: grid-template-columns 0.22s ease;
}
.app-shell--collapsed {
  grid-template-columns: 76px minmax(0, 1fr);
}
.content-island {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  border: 1px solid #e4e9f3;
  border-radius: 26px;
  background: #f7f9fd;
  box-shadow: 0 24px 70px #01081857;
}
.content-header {
  display: flex;
  flex: none;
  align-items: flex-start;
  gap: 24px;
  min-height: 158px;
  padding: 42px 52px 34px;
  border-bottom: 1px solid #e5eaf3;
  background: #fff;
}
.content-heading {
  flex: 1;
  min-width: 0;
}
.content-eyebrow {
  margin: 0 0 13px;
  color: #3457f0;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.17em;
}
.content-eyebrow span {
  padding: 0 8px;
  color: #aeb8cc;
}
.content-heading h1 {
  margin: 0;
  color: #0f172a;
  font-size: clamp(28px, 2.7vw, 36px);
  font-weight: 750;
  letter-spacing: -0.045em;
  line-height: 1.13;
}
.content-description {
  margin: 9px 0 0;
  color: #65728a;
  font-size: 14px;
}
.header-account {
  display: flex;
  align-items: center;
  gap: 9px;
  max-width: 180px;
  margin-top: 8px;
  padding: 9px 13px;
  overflow: hidden;
  border: 1px solid #e3e9f3;
  border-radius: 999px;
  background: #f9fbff;
  color: #42516b;
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-account-dot {
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 50%;
  background: #17915a;
  box-shadow: 0 0 0 3px #dff6eb;
}
.content-body {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  -webkit-overflow-scrolling: touch;
  padding: 40px 52px 64px;
}
.admin-shell-header {
  display: flex;
  flex: none;
  align-items: center;
  gap: 16px;
  min-height: 68px;
  padding: 12px 32px;
  border-bottom: 1px solid #e1e6f0;
  background: #fff;
}
.admin-shell-header-content {
  flex: 1;
  min-width: 0;
}
.admin-shell-header-content:empty,
.admin-shell-header:has(.admin-shell-header-content:not(:empty)) .admin-shell-fallback {
  display: none;
}
.admin-shell-fallback {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
}
.app-shell--admin .content-body {
  padding: 24px 32px 48px;
  background: #f4f6fb;
}
.mobile-menu-button {
  display: none;
  width: 42px;
  height: 42px;
  flex: none;
  place-items: center;
  border: 1px solid #e2e8f3;
  border-radius: 11px;
  background: #fff;
  color: #0f172a;
  cursor: pointer;
}
.mobile-menu-button:focus-visible {
  outline: 3px solid #3457f0;
  outline-offset: 3px;
}
.navigation-backdrop {
  display: none;
}
@media (max-width: 1199px) {
  .content-header {
    padding-right: 36px;
    padding-left: 36px;
  }
  .content-body {
    padding-right: 36px;
    padding-left: 36px;
  }
}
@media (max-width: 767px) {
  .app-shell,
  .app-shell--collapsed {
    display: block;
    padding: 9px;
  }
  .content-island {
    border-radius: 20px;
  }
  .content-header {
    align-items: flex-start;
    min-height: 150px;
    gap: 14px;
    padding: 25px 21px 27px;
  }
  .mobile-menu-button {
    display: grid;
  }
  .content-eyebrow {
    margin-top: 3px;
    font-size: 9px;
  }
  .content-heading h1 {
    font-size: 28px;
  }
  .content-description {
    font-size: 12px;
  }
  .content-body {
    padding: 25px 20px 40px;
  }
  .admin-shell-header {
    padding: 16px 20px;
  }
  .app-shell--admin .content-body {
    padding: 20px 16px 36px;
  }
  .header-account {
    display: none;
  }
  .navigation-backdrop {
    position: fixed;
    z-index: 20;
    inset: 0;
    display: block;
    width: 100%;
    border: 0;
    background: #061024a6;
  }
}
@media (prefers-reduced-motion: reduce) {
  .app-shell {
    transition: none;
  }
}
</style>
