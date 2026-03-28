"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { setTokenGetter } from "@/shared/api/client";
import { getMe } from "./api";
import type { User, AuthState } from "./types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  authState: AuthState;
  setToken: (token: string) => void;
  clearAuth: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("auth_token");
    }
    return null;
  });
  const [authState, setAuthState] = useState<AuthState>("loading");

  const setToken = useCallback((newToken: string) => {
    localStorage.setItem("auth_token", newToken);
    setTokenState(newToken);
  }, []);

  const clearAuth = useCallback(() => {
    localStorage.removeItem("auth_token");
    setTokenState(null);
    setUser(null);
    setAuthState("unauthenticated");
  }, []);

  // Wire token into the API client
  useEffect(() => {
    setTokenGetter(() => token);
  }, [token]);

  // When token changes, validate it by calling /auth/me
  useEffect(() => {
    if (!token) {
      setAuthState("unauthenticated");
      return;
    }

    setAuthState("loading");
    getMe()
      .then((u) => {
        setUser(u);
        setAuthState("authenticated");
      })
      .catch(() => {
        setTokenState(null);
        setUser(null);
        setAuthState("unauthenticated");
      });
  }, [token]);

  return (
    <AuthContext.Provider value={{ user, token, authState, setToken, clearAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
