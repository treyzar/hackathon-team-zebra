import type { AxiosError, InternalAxiosRequestConfig } from "axios";
import type { Pinia } from "pinia";

import { api } from "./http";
import { useAuthStore } from "@/stores/auth";

declare module "axios" {
  export interface AxiosRequestConfig {
    _retry?: boolean;
  }
}

let refreshPromise: Promise<string> | null = null;

function setAuthorizationHeader(config: InternalAxiosRequestConfig, token: string): void {
  config.headers.set("Authorization", `Bearer ${token}`);
}

export function setupApiInterceptors(pinia: Pinia): void {
  api.interceptors.request.use((config) => {
    const auth = useAuthStore(pinia);

    if (auth.accessToken) {
      setAuthorizationHeader(config, auth.accessToken);
    }

    return config;
  });

  api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config;

      if (error.response?.status !== 401 || !originalRequest || originalRequest._retry) {
        return Promise.reject(error);
      }

      const auth = useAuthStore(pinia);

      if (!auth.refreshToken) {
        auth.clearTokens();
        return Promise.reject(error);
      }

      originalRequest._retry = true;
      const pendingRefresh = refreshPromise ?? (refreshPromise = auth.refreshAccessToken());

      try {
        const accessToken = await pendingRefresh;
        setAuthorizationHeader(originalRequest, accessToken);
        return api.request(originalRequest);
      } catch {
        auth.clearTokens();
        return Promise.reject(error);
      } finally {
        if (refreshPromise === pendingRefresh) {
          refreshPromise = null;
        }
      }
    },
  );
}
