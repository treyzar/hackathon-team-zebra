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
  min-height: 320px;
  padding: 42px;
  border: 1px solid #e0e7f1;
  border-radius: 18px;
  background: #fff;
}
.empty-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 14px;
  background: #eaf0fe;
  color: #3457f0;
}
.empty-kicker {
  margin: 28px 0 9px;
  color: #3457f0;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.17em;
}
.section-empty h2 {
  margin: 0;
  color: #0f172a;
  font-size: 28px;
  letter-spacing: -0.035em;
}
.section-empty > p:not(.empty-kicker) {
  margin: 9px 0 0;
  color: #65728a;
  font-size: 14px;
}
.section-empty a {
  margin-top: 32px;
  color: #3457f0;
  font-size: 13px;
  font-weight: 700;
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
