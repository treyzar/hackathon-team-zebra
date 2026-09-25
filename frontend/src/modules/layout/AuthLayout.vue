<script setup lang="ts">
import "./auth.css";

defineProps<{ title: string; subtitle?: string }>();
</script>

<template>
  <main class="auth-page">
    <section class="auth-intro">
      <div class="auth-brand">
        <span class="auth-brand-mark" aria-hidden="true">&lt;/&gt;</span>
        <strong>Код роста</strong>
      </div>
      <div class="auth-intro-copy">
        <p class="auth-headline">Учимся программировать<br />шаг за шагом</p>
        <p class="auth-lead">
          Scratch, Minecraft Education и Python для 1–9 классов. Федерация спортивного
          программирования Чувашской Республики.
        </p>
      </div>
    </section>
    <section class="auth-card">
      <h1>{{ title }}</h1>
      <p v-if="subtitle" class="auth-subtitle">{{ subtitle }}</p>
      <slot />
      <p class="auth-footer"><slot name="footer" /></p>
    </section>
  </main>
</template>
