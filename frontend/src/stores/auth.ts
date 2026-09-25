import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { api, authApi, type TokenResponse, type UserResponse, type UserRole } from "@/api/http";

interface Credentials {
  username: string;
  password: string;
}

interface SignupData extends Credentials {
  email: string;
  name: string;
  surname: string;
  patronymic: string;
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
  const user = ref<UserResponse | null>(null);
  const role = computed(() => user.value?.role ?? null);
  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value));
  let profilePromise: Promise<UserResponse> | null = null;
  let sessionVersion = 0;

  function hasRole(...roles: UserRole[]): boolean {
    return isAuthenticated.value && role.value !== null && roles.includes(role.value);
  }

  function setTokens(tokens: TokenResponse): void {
    accessToken.value = tokens.access_token;
    refreshToken.value = tokens.refresh_token;
    persistTokens({
      accessToken: accessToken.value,
      refreshToken: refreshToken.value,
    });
  }

  function clearTokens(): void {
    sessionVersion += 1;
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    profilePromise = null;
    persistTokens(null);
  }

  function loadCurrentUser(): Promise<UserResponse> {
    if (!accessToken.value) {
      return Promise.reject(new Error("No access token available"));
    }

    if (!profilePromise) {
      const version = sessionVersion;
      const pending = api.get<UserResponse>("/user/me").then(({ data }) => {
        if (version === sessionVersion) {
          user.value = data;
        }
        return data;
      });
      const currentPromise = pending.finally(() => {
        if (profilePromise === currentPromise) {
          profilePromise = null;
        }
      });
      profilePromise = currentPromise;
    }

    return profilePromise;
  }

  async function restoreSession(): Promise<void> {
    if (!accessToken.value || user.value) {
      return;
    }

    try {
      await loadCurrentUser();
    } catch {
      // A failed profile request leaves the route unauthenticated; retry on the next navigation.
    }
  }

  async function login(credentials: Credentials): Promise<TokenResponse> {
    const { data } = await authApi.post<TokenResponse>("/auth/login", credentials);
    sessionVersion += 1;
    user.value = null;
    setTokens(data);
    try {
      await loadCurrentUser();
    } catch (error) {
      clearTokens();
      throw error;
    }
    return data;
  }

  async function signup(data: SignupData): Promise<TokenResponse> {
    const { data: tokens } = await authApi.post<TokenResponse>("/auth/signup", data);
    sessionVersion += 1;
    user.value = null;
    setTokens(tokens);
    try {
      await loadCurrentUser();
    } catch (error) {
      clearTokens();
      throw error;
    }
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
    user,
    role,
    isAuthenticated,
    hasRole,
    setTokens,
    clearTokens,
    loadCurrentUser,
    restoreSession,
    login,
    signup,
    refreshAccessToken,
    logout,
  };
});
