<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { navigationForRole } from "@/modules/navigation/items";
import NavigationRail from "@/modules/navigation/NavigationRail.vue";
import SideNavigation from "@/modules/navigation/SideNavigation.vue";
import TopNavigation from "@/modules/navigation/TopNavigation.vue";
import { LOGIN_ROUTE } from "@/pages/login/constants";
import { STUDENT_COURSE_ROUTE } from "@/pages/student/course/constants";
import { STUDENT_STEP_ROUTE } from "@/pages/student/step/constants";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const menuOpen = ref(false);
const contentBody = ref<HTMLElement | null>(null);

// Each cabinet has its own navigation in the mockups: students get a light top bar,
// curators a sidebar, admins an icon rail that opens the full menu as a drawer.
const layout = computed(() => {
  if (auth.role === "student") return "top";
  if (auth.role === "admin") return "rail";
  return "side";
});
const username = computed(() => auth.user?.username ?? "");
const homeItem = computed(() => navigationForRole(auth.role)[0]);
const pageTitle = computed(
  () => (route.meta.title as string | undefined) ?? homeItem.value?.label ?? "Главная",
);
const pageDescription = computed(
  () => (route.meta.description as string | undefined) ?? homeItem.value?.description ?? "",
);
const isStudentCourse = computed(
  () =>
    auth.role === "student" &&
    (route.name === STUDENT_COURSE_ROUTE.name || route.name === STUDENT_STEP_ROUTE.name),
);

watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false;
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
    :class="[`app-shell--${layout}`, { 'app-shell--student-course': isStudentCourse }]"
  >
    <TopNavigation
      v-if="layout === 'top'"
      :role="auth.role"
      :username="username"
      :menu-open="menuOpen"
      @open-menu="menuOpen = true"
      @logout="logout"
    />
    <NavigationRail
      v-else-if="layout === 'rail'"
      class="app-shell-navigation"
      :role="auth.role"
      :username="username"
      :menu-open="menuOpen"
      @open-menu="menuOpen = true"
    />
    <SideNavigation
      v-else
      class="app-shell-navigation"
      :role="auth.role"
      :username="username"
      @logout="logout"
    />

    <template v-if="menuOpen">
      <button
        class="navigation-backdrop"
        type="button"
        aria-label="Закрыть меню"
        tabindex="-1"
        @click="menuOpen = false"
      />
      <SideNavigation
        overlay
        :role="auth.role"
        :username="username"
        @navigate="menuOpen = false"
        @close="menuOpen = false"
        @logout="logout"
      />
    </template>

    <main class="app-main">
      <header v-if="layout !== 'top'" class="page-header">
        <button
          class="page-menu-button"
          type="button"
          aria-label="Открыть меню"
          aria-controls="app-navigation"
          :aria-expanded="menuOpen"
          @click="menuOpen = true"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
        </button>
        <!-- Admin pages teleport their own title and actions here. -->
        <div v-if="layout === 'rail'" id="admin-page-header" class="page-header-slot" />
        <div class="page-header-fallback">
          <h1>{{ pageTitle }}</h1>
          <p v-if="layout === 'side' && pageDescription">{{ pageDescription }}</p>
        </div>
      </header>

      <div
        ref="contentBody"
        class="content-body"
        role="region"
        aria-label="Содержимое страницы"
        tabindex="-1"
      >
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  background: var(--color-bg);
  color: var(--color-text);
}
.app-shell--top {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr);
}
.app-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.page-header {
  display: flex;
  flex: none;
  align-items: center;
  gap: 16px;
  padding: 24px 32px 0;
}
.app-shell--rail .page-header {
  min-height: 68px;
  padding: 12px 32px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}
.page-header-slot {
  flex: 1;
  min-width: 0;
}
.page-header-slot:empty,
.page-header:has(.page-header-slot:not(:empty)) .page-header-fallback {
  display: none;
}
.page-header-fallback {
  flex: 1;
  min-width: 0;
}
.page-header-fallback h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}
.page-header-fallback p {
  margin: 4px 0 0;
  color: var(--color-muted);
  font-size: 14px;
}
.content-body {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  padding: 24px 32px 48px;
  outline: none;
}
.app-shell--top .content-body {
  padding: 32px 48px 56px;
}
.app-shell--student-course .content-body {
  overflow: hidden;
  padding: 0;
}
.page-menu-button {
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
.page-menu-button svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
}
.navigation-backdrop {
  position: fixed;
  z-index: 30;
  inset: 0;
  width: 100%;
  padding: 0;
  border: 0;
  background: #0b122059;
  cursor: default;
}
@media (max-width: 1100px) {
  .app-shell--top .content-body {
    padding-right: 24px;
    padding-left: 24px;
  }
}
@media (max-width: 767px) {
  .app-shell {
    grid-template-columns: minmax(0, 1fr);
  }
  .app-shell-navigation {
    display: none;
  }
  .page-header,
  .app-shell--rail .page-header {
    padding: 16px;
  }
  .page-menu-button {
    display: grid;
  }
  .page-header-fallback h1 {
    font-size: 24px;
  }
  .content-body,
  .app-shell--top .content-body {
    padding: 20px 16px 36px;
  }
  .app-shell--student-course .content-body {
    padding: 0;
  }
}
</style>
