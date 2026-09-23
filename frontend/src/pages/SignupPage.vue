<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { getApiErrorMessage } from "@/api/errors";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const form = reactive({
  email: "",
  username: "",
  password: "",
  confirmPassword: "",
});
const errorMessage = ref("");
const isSubmitting = ref(false);
const passwordsMatch = computed(() => form.password === form.confirmPassword);

async function submit(): Promise<void> {
  if (isSubmitting.value) {
    return;
  }

  if (!passwordsMatch.value) {
    errorMessage.value = "Пароли не совпадают.";
    return;
  }

  errorMessage.value = "";
  isSubmitting.value = true;

  try {
    await auth.signup({
      email: form.email,
      username: form.username,
      password: form.password,
    });
    await router.replace({ name: "dashboard" });
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
        <h1 class="text-3xl font-semibold tracking-tight">Создать аккаунт</h1>
        <p class="mt-2 text-slate-600">Регистрация занимает меньше минуты.</p>
      </div>

      <form class="space-y-5" @submit.prevent="submit">
        <label class="block space-y-2">
          <span class="text-sm font-medium">Email</span>
          <input
            v-model.trim="form.email"
            class="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none transition focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
            type="email"
            name="email"
            autocomplete="email"
            required
          />
        </label>

        <label class="block space-y-2">
          <span class="text-sm font-medium">Логин</span>
          <input
            v-model.trim="form.username"
            class="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none transition focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
            name="username"
            autocomplete="username"
            minlength="6"
            maxlength="20"
            pattern="[a-zA-Z0-9_-]+"
            required
          />
          <span class="block text-xs text-slate-500"
            >От 6 до 20 символов: латиница, цифры, _ или -.</span
          >
        </label>

        <label class="block space-y-2">
          <span class="text-sm font-medium">Пароль</span>
          <input
            v-model="form.password"
            class="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none transition focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
            type="password"
            name="password"
            autocomplete="new-password"
            minlength="8"
            maxlength="64"
            required
          />
        </label>

        <label class="block space-y-2">
          <span class="text-sm font-medium">Повторите пароль</span>
          <input
            v-model="form.confirmPassword"
            class="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none transition focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
            :class="{
              'border-rose-500 focus:border-rose-600 focus:ring-rose-100':
                form.confirmPassword && !passwordsMatch,
            }"
            type="password"
            name="confirm-password"
            autocomplete="new-password"
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
          {{ isSubmitting ? "Создаём аккаунт…" : "Зарегистрироваться" }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-slate-600">
        Уже есть аккаунт?
        <RouterLink class="font-medium text-indigo-600 hover:text-indigo-700" to="/login"
          >Войти</RouterLink
        >
      </p>
    </section>
  </main>
</template>
