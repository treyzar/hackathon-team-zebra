<script setup lang="ts">
import type { NavigationIconName } from "./items";

defineProps<{ name: NavigationIconName }>();
</script>

<template>
  <svg
    class="navigation-icon"
    xmlns="http://www.w3.org/2000/svg"
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'home'">
      <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
      <path d="M9 21v-7h6v7" />
    </template>
    <template v-else-if="name === 'courses'">
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5z" />
      <path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20M8 7h8" />
    </template>
    <template v-else-if="name === 'skills'">
      <circle cx="12" cy="5" r="2" />
      <circle cx="5" cy="18" r="2" />
      <circle cx="19" cy="18" r="2" />
      <path d="m11 7-5 9m7-9 5 9M7 18h10" />
    </template>
    <template v-else-if="name === 'history'">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </template>
    <template v-else-if="name === 'progress'">
      <path d="M4 20V13m5 7V8m5 12v-5m5 5V4" />
      <path d="M2 20h20" />
    </template>
    <template v-else-if="name === 'learners' || name === 'users'">
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20v-2a6 6 0 0 1 12 0v2M17 5a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 5" />
    </template>
    <template v-else-if="name === 'reviews'">
      <path d="M4 4h16v16H4zM4 15h5l2 2h2l2-2h5" />
      <path d="M8 8h8m-8 3h6" />
    </template>
    <template v-else-if="name === 'questions'">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9a2.5 2.5 0 1 1 4.1 1.9C12.5 11.8 12 12.3 12 13.5M12 17h.01" />
    </template>
    <template v-else-if="name === 'builder'">
      <path d="M3 4h18v16H3zM9 4v16M9 10h12" />
      <path d="M5.5 8h1M5.5 12h1M5.5 16h1" />
    </template>
    <template v-else-if="name === 'groups'">
      <circle cx="8" cy="8" r="2.5" />
      <circle cx="17" cy="8" r="2.5" />
      <path d="M2.5 19v-1.5a5.5 5.5 0 0 1 11 0V19zm9 0v-1.5a5.5 5.5 0 0 1 10 0V19" />
    </template>
  </svg>
</template>
