"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { callback } from "@/domains/auth/api";
import { useAuth } from "@/domains/auth/auth-provider";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setToken } = useAuth();
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    const code = searchParams.get("code");
    if (!code) {
      router.push("/login");
      return;
    }

    callback(code)
      .then((res) => {
        setToken(res.access_token);
        router.push("/workspaces");
      })
      .catch(() => {
        router.push("/login");
      });
  }, [searchParams, setToken, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Signing in...</p>
    </div>
  );
}
