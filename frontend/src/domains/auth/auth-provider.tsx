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
  const [token, setTokenState] = useState<string | null>(null);
  const [authState, setAuthState] = useState<AuthState>("loading");

  const setToken = useCallback((newToken: string) => {
    setTokenState(newToken);
  }, []);

  const clearAuth = useCallback(() => {
    setTokenState(null);
    setUser(null);
    setAuthState("unauthenticated");
  }, []);

  // Wire token into the API client
  useEffect(() => {
    setTokenGetter(() => token);
  }, [token]);

  // On mount: in MSW/dev mode, auto-set a dev token
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_ENABLE_MSW === "true" && !token) {
      setTokenState("dev-jwt-token-for-testing");
    }
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
