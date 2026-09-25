<script setup lang="ts">
import { reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { getApiErrorMessage } from "@/api/errors";
import AuthLayout from "@/modules/layout/AuthLayout.vue";
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
  <AuthLayout title="Вход" subtitle="Войдите, чтобы продолжить работу.">
    <form class="auth-form" @submit.prevent="submit">
      <label class="auth-field">
        <span>Логин</span>
        <input v-model.trim="form.username" name="username" autocomplete="username" required />
      </label>

      <label class="auth-field">
        <span>Пароль</span>
        <input
          v-model="form.password"
          type="password"
          name="password"
          autocomplete="current-password"
          required
        />
      </label>

      <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>

      <button class="auth-submit" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? "Входим…" : "Войти" }}
      </button>
    </form>

    <template #footer>
      Нет аккаунта? <RouterLink :to="SIGNUP_ROUTE.path">Создать аккаунт</RouterLink>
    </template>
  </AuthLayout>
</template>
