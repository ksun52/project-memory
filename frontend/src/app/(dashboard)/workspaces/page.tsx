"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/shared/components/breadcrumbs";
import { PageHeader } from "@/shared/components/page-header";
import { WorkspaceList } from "@/domains/workspace/components/workspace-list";
import { WorkspaceCreateDialog } from "@/domains/workspace/components/workspace-create-dialog";

export default function WorkspacesPage() {
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Workspaces" }]} />
      <PageHeader
        title="Workspaces"
        description="Manage your project workspaces"
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Workspace
          </Button>
        }
      />
      <WorkspaceList />
      <WorkspaceCreateDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
