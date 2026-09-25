<script setup lang="ts">
import AppShell from "@/modules/layout/AppShell.vue";
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <AppShell v-if="route.meta.requiresAuth">
      <component :is="Component" />
    </AppShell>
    <component :is="Component" v-else />
  </RouterView>
</template>
