"use client";

import { useState } from "react";
import { use } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/shared/components/breadcrumbs";
import { PageHeader } from "@/shared/components/page-header";
import { PageSkeleton } from "@/shared/components/loading-skeleton";
import { MemorySpaceList } from "@/domains/memory-space/components/memory-space-list";
import { MemorySpaceCreateDialog } from "@/domains/memory-space/components/memory-space-create-dialog";
import { useWorkspace } from "@/domains/workspace/hooks";

interface WorkspaceDetailPageProps {
  params: Promise<{ workspaceId: string }>;
}

export default function WorkspaceDetailPage({ params }: WorkspaceDetailPageProps) {
  const { workspaceId } = use(params);
  const { data: workspace, isLoading } = useWorkspace(workspaceId);
  const [createOpen, setCreateOpen] = useState(false);

  if (isLoading) {
    return <PageSkeleton />;
  }

  const workspaceName = workspace?.name ?? "Workspace";

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: "Workspaces", href: "/workspaces" },
          { label: workspaceName },
        ]}
      />
      <PageHeader
        title={workspaceName}
        description={workspace?.description || "Manage memory spaces in this workspace"}
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Memory Space
          </Button>
        }
      />
      <MemorySpaceList workspaceId={workspaceId} />
      <MemorySpaceCreateDialog
        workspaceId={workspaceId}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </div>
  );
}
