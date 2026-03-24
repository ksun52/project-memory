"use client";

import Link from "next/link";
import { MoreHorizontal, Pencil, Trash2, Archive, RotateCcw } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import type { MemorySpace } from "../types";

interface MemorySpaceCardProps {
  memorySpace: MemorySpace;
  onEdit: (memorySpace: MemorySpace) => void;
  onDelete: (memorySpace: MemorySpace) => void;
  onToggleStatus: (memorySpace: MemorySpace) => void;
}

export function MemorySpaceCard({
  memorySpace,
  onEdit,
  onDelete,
  onToggleStatus,
}: MemorySpaceCardProps) {
  const isArchived = memorySpace.status === "archived";

  return (
    <Card className="relative hover:border-foreground/20 transition-colors">
      <Link
        href={`/workspaces/${memorySpace.workspace_id}/memory-spaces/${memorySpace.id}`}
        className="absolute inset-0 z-0"
      >
        <span className="sr-only">Open {memorySpace.name}</span>
      </Link>
      <CardHeader>
        <div className="flex items-center gap-2 min-w-0">
          <CardTitle className="truncate">{memorySpace.name}</CardTitle>
          <Badge variant={isArchived ? "secondary" : "default"}>
            {memorySpace.status}
          </Badge>
        </div>
        <CardAction>
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button variant="ghost" size="icon-sm" className="relative z-10" />
              }
            >
              <MoreHorizontal className="h-4 w-4" />
              <span className="sr-only">Actions</span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(memorySpace)}>
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onToggleStatus(memorySpace)}>
                {isArchived ? (
                  <>
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Activate
                  </>
                ) : (
                  <>
                    <Archive className="h-4 w-4 mr-2" />
                    Archive
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => onDelete(memorySpace)}
                className="text-destructive"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardAction>
        <CardDescription className="line-clamp-2">
          {memorySpace.description || "No description"}
        </CardDescription>
      </CardHeader>
    </Card>
  );
}
