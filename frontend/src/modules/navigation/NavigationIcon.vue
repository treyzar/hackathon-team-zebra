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
      <path
        d="M4 5h6a2 2 0 0 1 2 2v12a2 2 0 0 0-2-2H4zM20 5h-6a2 2 0 0 0-2 2v12a2 2 0 0 1 2-2h6z"
      />
    </template>
    <template v-else-if="name === 'skills'">
      <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14" />
    </template>
    <template v-else-if="name === 'history'">
      <path d="m4 13 2-8h12l2 8v6H4zM4 13h5l1 2h4l1-2h5" />
    </template>
    <template v-else-if="name === 'progress'">
      <path d="M4 20V13m5 7V8m5 12v-5m5 5V4" />
      <path d="M2 20h20" />
    </template>
    <template v-else-if="name === 'users'">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <circle cx="9" cy="11" r="2" />
      <path d="M6 16c.6-1.4 1.7-2 3-2s2.4.6 3 2M14 10h4M14 13h3" />
    </template>
    <template v-else-if="name === 'learners'">
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
    <template v-else-if="name === 'deadlines'">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M7 3v4M17 3v4M3 10h18M8 15h3M8 18h3" />
    </template>
    <template v-else-if="name === 'builder'">
      <path d="M3 4h18v16H3zM9 4v16M9 10h12" />
      <path d="M5.5 8h1M5.5 12h1M5.5 16h1" />
    </template>
    <template v-else-if="name === 'groups'">
      <circle cx="9" cy="8" r="3" />
      <path d="M3 19c0-3 2.7-5 6-5s6 2 6 5M16 5.2a3 3 0 0 1 0 5.6M18 14.5c1.8.6 3 2.2 3 4.5" />
    </template>
  </svg>
</template>
