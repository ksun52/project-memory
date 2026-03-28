import { apiClient } from "@/shared/api/client";
import type { User } from "./types";

export function getMe(): Promise<User> {
  return apiClient.get<User>("/auth/me");
}

export function login(): Promise<{ redirect_url: string }> {
  return apiClient.get<{ redirect_url: string }>("/auth/login");
}

export function logout(): Promise<void> {
  return apiClient.post("/auth/logout");
}
