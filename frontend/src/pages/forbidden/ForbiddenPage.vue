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
  min-height: 320px;
  flex-direction: column;
  align-items: flex-start;
  padding: 42px;
  border: 1px solid #e0e7f1;
  border-radius: 18px;
  background: #fff;
}
.forbidden-page > span {
  color: #3457f0;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.12em;
}
.forbidden-page h2 {
  margin: 20px 0 8px;
  color: #0f172a;
  font-size: 27px;
  letter-spacing: -0.03em;
}
.forbidden-page p {
  margin: 0;
  color: #65728a;
  font-size: 14px;
}
.forbidden-page a {
  margin-top: 32px;
  color: #3457f0;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}
.forbidden-page a:hover {
  text-decoration: underline;
}
</style>
