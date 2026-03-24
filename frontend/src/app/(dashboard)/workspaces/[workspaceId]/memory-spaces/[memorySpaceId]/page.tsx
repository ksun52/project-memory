"use client";

import { use } from "react";
import { Brain, FileText, ListChecks, ScrollText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Breadcrumbs } from "@/shared/components/breadcrumbs";
import { PageHeader } from "@/shared/components/page-header";
import { PageSkeleton } from "@/shared/components/loading-skeleton";
import { useWorkspace } from "@/domains/workspace/hooks";
import { useMemorySpace } from "@/domains/memory-space/hooks";

interface MemorySpaceDetailPageProps {
  params: Promise<{ workspaceId: string; memorySpaceId: string }>;
}

export default function MemorySpaceDetailPage({ params }: MemorySpaceDetailPageProps) {
  const { workspaceId, memorySpaceId } = use(params);
  const { data: workspace, isLoading: workspaceLoading } = useWorkspace(workspaceId);
  const { data: memorySpace, isLoading: memorySpaceLoading } = useMemorySpace(memorySpaceId);

  if (workspaceLoading || memorySpaceLoading) {
    return <PageSkeleton />;
  }

  const workspaceName = workspace?.name ?? "Workspace";
  const memorySpaceName = memorySpace?.name ?? "Memory Space";
  const isArchived = memorySpace?.status === "archived";

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: "Workspaces", href: "/workspaces" },
          { label: workspaceName, href: `/workspaces/${workspaceId}` },
          { label: memorySpaceName },
        ]}
      />
      <PageHeader
        title={
          <div className="flex items-center gap-3">
            {memorySpaceName}
            <Badge variant={isArchived ? "secondary" : "default"}>
              {memorySpace?.status ?? "active"}
            </Badge>
          </div>
        }
        description={memorySpace?.description || "No description"}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <PlaceholderCard
          icon={<FileText className="h-5 w-5 text-muted-foreground" />}
          title="Sources"
          description="Upload and manage source documents"
        />
        <PlaceholderCard
          icon={<ListChecks className="h-5 w-5 text-muted-foreground" />}
          title="Records"
          description="View extracted memory records"
        />
        <PlaceholderCard
          icon={<ScrollText className="h-5 w-5 text-muted-foreground" />}
          title="Summary"
          description="Generate project one-pagers"
        />
      </div>

      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <Brain className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-lg font-medium">Coming in Phase 2</p>
          <p className="text-sm text-muted-foreground mt-1">
            Sources, Records, and Summary tabs will be available here.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function PlaceholderCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Card className="opacity-60">
      <CardHeader>
        <div className="flex items-center gap-2">
          {icon}
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
