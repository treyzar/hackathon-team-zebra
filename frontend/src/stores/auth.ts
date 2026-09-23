import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { authApi, type TokenResponse } from "@/api/http";

interface Credentials {
  username: string;
  password: string;
}

interface SignupData extends Credentials {
  email: string;
}

interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

const STORAGE_KEY = "zebra.auth.tokens";

function loadTokens(): StoredTokens | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "null");

    if (
      typeof value === "object" &&
      value !== null &&
      "accessToken" in value &&
      "refreshToken" in value &&
      typeof value.accessToken === "string" &&
      typeof value.refreshToken === "string"
    ) {
      return value as StoredTokens;
    }
  } catch {
    // A malformed value is treated as an expired session.
  }

  window.localStorage.removeItem(STORAGE_KEY);
  return null;
}

function persistTokens(tokens: StoredTokens | null): void {
  if (typeof window === "undefined") {
    return;
  }

  if (tokens) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

export const useAuthStore = defineStore("auth", () => {
  const initialTokens = loadTokens();
  const accessToken = ref<string | null>(initialTokens?.accessToken ?? null);
  const refreshToken = ref<string | null>(initialTokens?.refreshToken ?? null);
  const isAuthenticated = computed(() => Boolean(accessToken.value && refreshToken.value));

  function setTokens(tokens: TokenResponse): void {
    accessToken.value = tokens.access_token;
    refreshToken.value = tokens.refresh_token;
    persistTokens({
      accessToken: accessToken.value,
      refreshToken: refreshToken.value,
    });
  }

  function clearTokens(): void {
    accessToken.value = null;
    refreshToken.value = null;
    persistTokens(null);
  }

  async function login(credentials: Credentials): Promise<TokenResponse> {
    const { data } = await authApi.post<TokenResponse>("/auth/login", credentials);
    setTokens(data);
    return data;
  }

  async function signup(data: SignupData): Promise<TokenResponse> {
    const { data: tokens } = await authApi.post<TokenResponse>("/auth/signup", data);
    setTokens(tokens);
    return tokens;
  }

  async function refreshAccessToken(): Promise<string> {
    if (!refreshToken.value) {
      throw new Error("No refresh token available");
    }

    const { data } = await authApi.post<TokenResponse>("/auth/refresh", {
      refresh_token: refreshToken.value,
    });
    setTokens(data);
    return data.access_token;
  }

  async function logout(): Promise<void> {
    const token = refreshToken.value;

    try {
      if (token) {
        await authApi.post("/auth/logout", { refresh_token: token });
      }
    } finally {
      clearTokens();
    }
  }

  return {
    accessToken,
    refreshToken,
    isAuthenticated,
    setTokens,
    clearTokens,
    login,
    signup,
    refreshAccessToken,
    logout,
  };
});
