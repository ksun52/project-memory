"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, FolderOpen, LogOut, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetTitle,
} from "@/components/ui/sheet";
import { useAuth } from "@/domains/auth/auth-provider";
import { useLogout } from "@/domains/auth/hooks";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Workspaces", href: "/workspaces", icon: FolderOpen },
];

function SidebarContent() {
  const pathname = usePathname();
  const { user } = useAuth();
  const logoutMutation = useLogout();

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-4 border-b">
        <Brain className="h-6 w-6 text-primary" />
        <span className="font-semibold text-lg">Project Memory</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User + Logout */}
      <div className="border-t px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">
              {user?.display_name}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {user?.email}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
          >
            <LogOut className="h-4 w-4" />
            <span className="sr-only">Log out</span>
          </Button>
        </div>
      </div>
    </div>
  );
}

export function AppSidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile: hamburger + sheet */}
      <div className="lg:hidden fixed top-0 left-0 z-40 p-3">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger
            render={<Button variant="outline" size="icon-sm" />}
          >
            <Menu className="h-4 w-4" />
            <span className="sr-only">Open menu</span>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0" showCloseButton={false}>
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <SidebarContent />
          </SheetContent>
        </Sheet>
      </div>

      {/* Desktop: fixed sidebar */}
      <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 border-r bg-background">
        <SidebarContent />
      </aside>
    </>
  );
}
