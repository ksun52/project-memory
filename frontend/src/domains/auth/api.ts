import { apiClient } from "@/shared/api/client";
import type { User, TokenResponse } from "./types";

export function getMe(): Promise<User> {
  return apiClient.get<User>("/auth/me");
}

export function login(): Promise<{ redirect_url: string }> {
  return apiClient.get<{ redirect_url: string }>("/auth/login");
}

export function callback(code: string): Promise<TokenResponse> {
  return apiClient.get<TokenResponse>(`/auth/callback?code=${encodeURIComponent(code)}`);
}

export function logout(): Promise<void> {
  return apiClient.post("/auth/logout");
}
