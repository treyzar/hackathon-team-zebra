<script setup lang="ts">
defineProps<{ username: string }>();
</script>

<template>
  <div class="catalog-greeting">
    <span class="catalog-greeting-message">Привет, {{ username || "ученик" }}! Продолжим?</span>
    <span v-if="username" class="catalog-greeting-user">{{ username }}</span>
  </div>
</template>

<style scoped>
.catalog-greeting {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 0 2px;
}
.catalog-greeting-message {
  color: #4a546b;
  font-size: 18px;
}
.catalog-greeting-user {
  margin-left: auto;
  color: #4a546b;
  font-size: 15px;
  font-weight: 600;
}
@media (max-width: 640px) {
  .catalog-greeting {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }
  .catalog-greeting-user {
    margin-left: 0;
  }
}
</style>
