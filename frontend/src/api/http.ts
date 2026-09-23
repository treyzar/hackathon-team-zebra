import axios from "axios";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface UserResponse {
  id: number;
  username: string;
  email: string;
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
});

// This client deliberately has no auth interceptors. It prevents a failed refresh
// request from trying to refresh itself again.
export const authApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
});
