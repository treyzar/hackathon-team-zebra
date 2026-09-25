<script setup lang="ts">
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
</script>

<template>
  <section class="forbidden-page">
    <span>403</span>
    <h2>У вас нет доступа к этому разделу</h2>
    <p>Вы можете вернуться в свой кабинет.</p>
    <RouterLink :to="DASHBOARD_ROUTE.path">На главную <span aria-hidden="true">→</span></RouterLink>
  </section>
</template>

<style scoped>
.forbidden-page {
  display: flex;
  min-height: 280px;
  flex-direction: column;
  align-items: flex-start;
  padding: 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}
.forbidden-page > span {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.12em;
}
.forbidden-page h2 {
  margin: 20px 0 8px;
  color: var(--color-text);
  font-size: 24px;
  font-weight: 700;
}
.forbidden-page p {
  margin: 0;
  color: var(--color-muted);
  font-size: 14px;
}
.forbidden-page a {
  margin-top: 32px;
  color: var(--color-primary);
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
}
.forbidden-page a:hover {
  text-decoration: underline;
}
</style>
