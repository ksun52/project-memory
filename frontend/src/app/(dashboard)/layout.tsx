"use client";

import { AuthGuard } from "@/domains/auth/components/auth-guard";
import { AppSidebar } from "@/shared/components/app-sidebar";
import { ErrorBoundary } from "@/shared/components/error-boundary";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="min-h-screen">
        <AppSidebar />
        <main className="lg:pl-64">
          <div className="px-6 py-8 max-w-7xl mx-auto">
            <ErrorBoundary>{children}</ErrorBoundary>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
