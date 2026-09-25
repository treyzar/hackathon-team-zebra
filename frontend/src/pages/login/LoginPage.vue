<script setup lang="ts">
import { reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { getApiErrorMessage } from "@/api/errors";
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
import { SIGNUP_ROUTE } from "@/pages/signup/constants";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const form = reactive({
  username: "",
  password: "",
});
const errorMessage = ref("");
const isSubmitting = ref(false);

async function submit(): Promise<void> {
  if (isSubmitting.value) {
    return;
  }

  errorMessage.value = "";
  isSubmitting.value = true;

  try {
    await auth.login(form);
    const redirect =
      typeof route.query.redirect === "string" ? route.query.redirect : DASHBOARD_ROUTE.path;
    await router.replace(redirect);
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error);
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <main class="grid min-h-screen place-items-center bg-slate-50 px-6 py-12 text-slate-950">
    <section class="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <div class="mb-8">
        <p class="mb-2 text-sm font-semibold tracking-[0.2em] text-indigo-600 uppercase">Zebra</p>
        <h1 class="text-3xl font-semibold tracking-tight">Логин</h1>
        <p class="mt-2 text-slate-600">Войдите, чтобы продолжить работу.</p>
      </div>

      <form class="space-y-5" @submit.prevent="submit">
        <label class="block space-y-2">
          <span class="text-sm font-medium">Логин</span>
          <input
            v-model.trim="form.username"
            class="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none transition focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
            name="username"
            autocomplete="username"
            required
          />
        </label>

        <label class="block space-y-2">
          <span class="text-sm font-medium">Пароль</span>
          <input
            v-model="form.password"
            class="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none transition focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
            type="password"
            name="password"
            autocomplete="current-password"
            required
          />
        </label>

        <p
          v-if="errorMessage"
          class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700"
          role="alert"
        >
          {{ errorMessage }}
        </p>

        <button
          class="w-full rounded-lg bg-indigo-600 px-4 py-2.5 font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          type="submit"
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? "Входим…" : "Войти" }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-slate-600">
        Нет аккаунта?
        <RouterLink
          class="font-medium text-indigo-600 hover:text-indigo-700"
          :to="SIGNUP_ROUTE.path"
          >Создать аккаунт</RouterLink
        >
      </p>
    </section>
  </main>
</template>
