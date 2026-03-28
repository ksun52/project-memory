export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export type AuthState = "loading" | "authenticated" | "unauthenticated";
