<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { getApiErrorMessage } from "@/api/errors";
import AuthLayout from "@/modules/layout/AuthLayout.vue";
import { DASHBOARD_ROUTE } from "@/pages/dashboard/constants";
import { LOGIN_ROUTE } from "@/pages/login/constants";
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
    await router.replace({ name: DASHBOARD_ROUTE.name });
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error);
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <AuthLayout title="Создать аккаунт" subtitle="Регистрация занимает меньше минуты.">
    <form class="auth-form" @submit.prevent="submit">
      <label class="auth-field">
        <span>Email</span>
        <input v-model.trim="form.email" type="email" name="email" autocomplete="email" required />
      </label>

      <label class="auth-field">
        <span>Логин</span>
        <input
          v-model.trim="form.username"
          name="username"
          autocomplete="username"
          minlength="6"
          maxlength="20"
          pattern="[a-zA-Z0-9_-]+"
          required
        />
        <span class="auth-hint">От 6 до 20 символов: латиница, цифры, _ или -.</span>
      </label>

      <label class="auth-field">
        <span>Пароль</span>
        <input
          v-model="form.password"
          type="password"
          name="password"
          autocomplete="new-password"
          minlength="8"
          maxlength="64"
          required
        />
      </label>

      <label class="auth-field">
        <span>Повторите пароль</span>
        <input
          v-model="form.confirmPassword"
          :aria-invalid="Boolean(form.confirmPassword) && !passwordsMatch"
          type="password"
          name="confirm-password"
          autocomplete="new-password"
          required
        />
      </label>

      <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>

      <button class="auth-submit" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? "Создаём аккаунт…" : "Зарегистрироваться" }}
      </button>
    </form>

    <template #footer>
      Уже есть аккаунт? <RouterLink :to="LOGIN_ROUTE.path">Войти</RouterLink>
    </template>
  </AuthLayout>
</template>
