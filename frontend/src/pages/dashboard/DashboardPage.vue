<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import NavigationIcon from "@/modules/navigation/NavigationIcon.vue";
import { navigationForRole } from "@/modules/navigation/items";
import { useAuthStore } from "@/stores/auth";
import { DASHBOARD_ROUTE } from "./constants";

const auth = useAuthStore();
const sections = computed(() =>
  navigationForRole(auth.role).filter((item) => item.path !== DASHBOARD_ROUTE.path),
);
const greetingTitle = computed(() =>
  auth.role === "student"
    ? `Привет, ${auth.user?.username}!`
    : `Здравствуйте, ${auth.user?.username}!`,
);
const greeting = computed(() => {
  if (auth.role === "student") return "Продолжай учиться в своём темпе.";
  if (auth.role === "curator") return "Всё для сопровождения учеников в одном месте.";
  return "Управляйте курсами и участниками платформы.";
});
</script>

<template>
  <section class="dashboard-welcome">
    <div class="welcome-copy">
      <span class="welcome-kicker">ВАШЕ ПРОСТРАНСТВО</span>
      <h2>{{ greetingTitle }}</h2>
      <p>{{ greeting }}</p>
    </div>
    <span class="welcome-symbol" aria-hidden="true">&lt;/&gt;</span>
  </section>

  <section class="dashboard-sections" aria-labelledby="dashboard-sections-heading">
    <div class="section-heading">
      <div>
        <p>БЫСТРЫЙ ДОСТУП</p>
        <h2 id="dashboard-sections-heading">Разделы кабинета</h2>
      </div>
      <span>{{ sections.length }} раздела</span>
    </div>
    <div class="section-grid">
      <RouterLink v-for="item in sections" :key="item.path" :to="item.path" class="section-card">
        <span class="section-icon"><NavigationIcon :name="item.icon" /></span>
        <strong>{{ item.label }}</strong>
        <span class="section-description">{{ item.description }}</span>
        <span class="section-arrow" aria-hidden="true">↗</span>
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.dashboard-welcome {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 212px;
  overflow: hidden;
  padding: 35px 42px;
  border: 1px solid #dbe4ff;
  border-radius: 20px;
  background: linear-gradient(115deg, #eaf0fe 0%, #f7f9ff 74%);
}
.dashboard-welcome::after {
  position: absolute;
  right: -70px;
  bottom: -120px;
  width: 300px;
  height: 300px;
  border: 1px solid #cbd7ff;
  border-radius: 50%;
  content: "";
}
.welcome-copy {
  position: relative;
  z-index: 1;
}
.welcome-kicker,
.section-heading p {
  color: #3457f0;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.17em;
}
.welcome-copy h2 {
  max-width: 560px;
  margin: 14px 0 10px;
  color: #0f172a;
  font-size: clamp(25px, 2.7vw, 36px);
  letter-spacing: -0.045em;
  line-height: 1.15;
}
.welcome-copy p {
  margin: 0;
  color: #56647e;
  font-size: 15px;
}
.welcome-symbol {
  position: relative;
  z-index: 1;
  margin-right: 16px;
  color: #3457f0;
  font-size: 64px;
  font-weight: 800;
  letter-spacing: -0.14em;
  transform: rotate(-8deg);
}
.dashboard-sections {
  margin-top: 40px;
}
.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.section-heading p {
  margin: 0 0 7px;
}
.section-heading h2 {
  margin: 0;
  color: #0f172a;
  font-size: 22px;
  letter-spacing: -0.025em;
}
.section-heading > span {
  padding-bottom: 3px;
  color: #7a879c;
  font-size: 12px;
}
.section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 15px;
}
.section-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 178px;
  padding: 22px;
  border: 1px solid #e0e7f1;
  border-radius: 16px;
  background: #fff;
  color: #0f172a;
  text-decoration: none;
  box-shadow: 0 6px 20px #17295008;
  transition:
    border-color 0.18s,
    transform 0.18s,
    box-shadow 0.18s;
}
.section-card:hover {
  transform: translateY(-3px);
  border-color: #aebffd;
  box-shadow: 0 14px 30px #17295012;
}
.section-card:focus-visible {
  outline: 3px solid #3457f0;
  outline-offset: 3px;
}
.section-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 11px;
  background: #eaf0fe;
  color: #3457f0;
}
.section-card strong {
  margin-top: 15px;
  font-size: 15px;
}
.section-description {
  margin-top: 5px;
  color: #6e7b91;
  font-size: 12px;
}
.section-arrow {
  position: absolute;
  top: 19px;
  right: 21px;
  color: #7e91b9;
  font-size: 20px;
}
@media (max-width: 767px) {
  .dashboard-welcome {
    min-height: 184px;
    padding: 27px;
  }
  .welcome-symbol {
    display: none;
  }
  .welcome-copy p {
    font-size: 13px;
  }
  .dashboard-sections {
    margin-top: 31px;
  }
}
</style>
