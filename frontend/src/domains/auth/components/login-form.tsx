"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { login } from "../api";

export function LoginForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleSignIn() {
    setLoading(true);
    try {
      const { redirect_url } = await login();
      router.push(redirect_url);
    } catch {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">Project Memory</h1>
        <p className="text-muted-foreground mt-2">
          Sign in to access your workspaces
        </p>
      </div>
      <Button onClick={handleSignIn} disabled={loading} size="lg">
        {loading ? "Signing in..." : "Sign in"}
      </Button>
    </div>
  );
}
