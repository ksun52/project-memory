"use client";

import { Suspense, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/domains/auth/auth-provider";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setToken } = useAuth();
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    const token = searchParams.get("token");
    if (!token) {
      router.push("/login");
      return;
    }

    setToken(token);
    router.push("/workspaces");
  }, [searchParams, setToken, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Signing in...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Signing in...</p>
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
