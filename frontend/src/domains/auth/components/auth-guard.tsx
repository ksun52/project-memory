"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../auth-provider";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { authState } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (authState === "unauthenticated") {
      router.push("/login");
    }
  }, [authState, router]);

  if (authState === "loading") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (authState === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}
