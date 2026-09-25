<script setup lang="ts">
import "./auth.css";

defineProps<{ title: string; subtitle: string }>();
</script>

<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="auth-brand">
        <span class="auth-brand-mark" aria-hidden="true">&lt;/&gt;</span>
        <span class="auth-brand-copy">
          <strong>Код роста</strong>
          <span>Платформа обучения</span>
        </span>
      </div>
      <h1>{{ title }}</h1>
      <p class="auth-subtitle">{{ subtitle }}</p>
      <slot />
      <p class="auth-footer"><slot name="footer" /></p>
    </section>
  </main>
</template>
