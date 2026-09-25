<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import NavigationIcon from "@/modules/navigation/NavigationIcon.vue";
import { navigationForRole } from "@/modules/navigation/items";
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const auth = useAuthStore();
const section = computed(() =>
  navigationForRole(auth.role).find((item) => item.path === route.path),
);
</script>

<template>
  <section class="section-empty">
    <span v-if="section" class="empty-icon"><NavigationIcon :name="section.icon" /></span>
    <p class="empty-kicker">РАЗДЕЛ КАБИНЕТА</p>
    <h2>{{ section?.label }}</h2>
    <p>{{ section?.description }}</p>
    <RouterLink :to="DASHBOARD_ROUTE.path"
      >Вернуться на главную <span aria-hidden="true">→</span></RouterLink
    >
  </section>
</template>

<style scoped>
.section-empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-height: 280px;
  padding: 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}
.empty-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: var(--radius-control);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.empty-kicker {
  margin: 28px 0 9px;
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.section-empty h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 24px;
  font-weight: 700;
}
.section-empty > p:not(.empty-kicker) {
  margin: 9px 0 0;
  color: var(--color-muted);
  font-size: 14px;
}
.section-empty a {
  margin-top: 32px;
  color: var(--color-primary);
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
}
.section-empty a:hover {
  text-decoration: underline;
}
@media (max-width: 767px) {
  .section-empty {
    padding: 27px;
  }
}
</style>
