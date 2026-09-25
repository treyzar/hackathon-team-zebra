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
  <div class="app-shell" :class="{ 'app-shell--collapsed': collapsed }">
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
      <header class="content-header">
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

      <div class="content-body">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 258px minmax(0, 1fr);
  min-height: 100vh;
  min-height: 100dvh;
  padding: 16px 16px 16px 0;
  background: #0b1220;
  transition: grid-template-columns 0.22s ease;
}
.app-shell--collapsed {
  grid-template-columns: 76px minmax(0, 1fr);
}
.content-island {
  min-width: 0;
  min-height: calc(100vh - 32px);
  min-height: calc(100dvh - 32px);
  overflow: hidden;
  border: 1px solid #e4e9f3;
  border-radius: 26px;
  background: #f7f9fd;
  box-shadow: 0 24px 70px #01081857;
}
.content-header {
  display: flex;
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
  padding: 40px 52px 64px;
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
    min-height: calc(100vh - 18px);
    min-height: calc(100dvh - 18px);
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
