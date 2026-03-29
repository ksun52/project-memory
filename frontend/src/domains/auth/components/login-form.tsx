"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { login } from "../api";

const API_ORIGIN = new URL(
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).origin;

export function LoginForm() {
  const [loading, setLoading] = useState(false);

  async function handleSignIn() {
    setLoading(true);
    try {
      const { redirect_url } = await login();
      // Absolute URLs (e.g. WorkOS) used as-is; relative URLs need the backend origin
      window.location.href = redirect_url.startsWith("http")
        ? redirect_url
        : `${API_ORIGIN}${redirect_url}`;
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
