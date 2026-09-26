<script setup lang="ts">
import { RouterLink } from "vue-router";

import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
</script>

<template>
  <RouterLink class="brand-mark" :to="DASHBOARD_ROUTE.path" aria-label="Код роста — главная">
    <span aria-hidden="true">&lt;/&gt;</span>
  </RouterLink>
</template>

<style scoped>
.brand-mark {
  display: grid;
  width: 40px;
  height: 40px;
  flex: none;
  place-items: center;
  border-radius: var(--radius-control);
  background: var(--color-primary);
  color: #fff;
  font-size: max(14px, var(--font-size-floor, 0px));
  font-weight: 800;
  letter-spacing: -0.08em;
  text-decoration: none;
}
.brand-mark:hover {
  background: var(--color-primary-hover);
  color: #fff;
}
</style>
