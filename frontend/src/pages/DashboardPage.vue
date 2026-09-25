<script setup lang="ts">
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();

async function logout(): Promise<void> {
  try {
    await auth.logout();
  } finally {
    await router.replace({ name: "login" });
  }
}
</script>

<template>
  <main class="min-h-screen bg-slate-50 px-6 py-12 text-slate-950">
    <section
      class="mx-auto flex max-w-4xl items-center justify-between rounded-2xl border border-slate-200 bg-white p-8 shadow-sm"
    >
      <div>
        <p class="text-sm font-semibold tracking-[0.2em] text-indigo-600 uppercase">Zebra Team</p>
        <h1 class="mt-2 text-3xl font-semibold tracking-tight">{{ auth.user?.username }}</h1>
        <p class="mt-2 text-slate-600">Роль: {{ auth.role }}</p>
      </div>
      <button
        class="rounded-lg border border-slate-300 px-4 py-2 font-medium transition hover:bg-slate-100"
        type="button"
        @click="logout"
      >
        Выйти
      </button>
    </section>
  </main>
</template>
