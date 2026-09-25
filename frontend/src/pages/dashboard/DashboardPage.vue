<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import NavigationIcon from "@/modules/navigation/NavigationIcon.vue";
import { navigationForRole } from "@/modules/navigation/items";
import CourseCatalog from "@/modules/student/courses/CourseCatalog.vue";
import { useAuthStore } from "@/stores/auth";
import { DASHBOARD_ROUTE } from "./constants";

const auth = useAuthStore();
const sections = computed(() =>
  navigationForRole(auth.role).filter((item) => item.path !== DASHBOARD_ROUTE.path),
);
const greeting = computed(() =>
  auth.role === "curator"
    ? "Всё для сопровождения учеников в одном месте."
    : "Управляйте курсами и участниками платформы.",
);
</script>

<template>
  <!-- The student's home in the mockups is their next step and courses. -->
  <CourseCatalog v-if="auth.role === 'student'" overview />
  <div v-else class="dashboard">
    <p class="dashboard-greeting">
      Здравствуйте, <b>{{ auth.user?.username }}</b
      >. {{ greeting }}
    </p>
    <div class="dashboard-grid">
      <RouterLink v-for="item in sections" :key="item.path" :to="item.path" class="dashboard-card">
        <span class="dashboard-icon"><NavigationIcon :name="item.icon" /></span>
        <strong>{{ item.label }}</strong>
        <span>{{ item.description }}</span>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1440px;
  margin: 0 auto;
  font-size: 14px;
  line-height: 1.5;
}
.dashboard-greeting {
  margin: 0;
  color: var(--color-muted);
  font-size: 15px;
}
.dashboard-greeting b {
  color: var(--color-text);
}
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.dashboard-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  color: var(--color-muted);
  text-decoration: none;
  transition: border-color 0.15s;
}
.dashboard-card:hover {
  border-color: var(--color-primary-pale);
  color: var(--color-muted);
}
.dashboard-card strong {
  margin-top: 8px;
  color: var(--color-text);
  font-size: 18px;
  font-weight: 600;
}
.dashboard-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
</style>
