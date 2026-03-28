"use client";

import { use } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useCallback } from "react";
import { Brain, FileText, ListChecks, ScrollText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Breadcrumbs } from "@/shared/components/breadcrumbs";
import { PageHeader } from "@/shared/components/page-header";
import { PageSkeleton } from "@/shared/components/loading-skeleton";
import { useWorkspace } from "@/domains/workspace/hooks";
import { useMemorySpace } from "@/domains/memory-space/hooks";
import { useSources } from "@/domains/source/hooks";
import { useRecords } from "@/domains/memory/hooks";
import { SourceList } from "@/domains/source/components/source-list";
import { RecordList } from "@/domains/memory/components/record-list";
import { SummaryPanel } from "@/domains/memory-space/components/summary-panel";
import { QueryPanel } from "@/domains/memory-space/components/query-panel";

const VALID_TABS = ["sources", "records", "summary", "ask"] as const;
type TabValue = (typeof VALID_TABS)[number];

interface MemorySpaceDetailPageProps {
  params: Promise<{ workspaceId: string; memorySpaceId: string }>;
}

export default function MemorySpaceDetailPage({ params }: MemorySpaceDetailPageProps) {
  const { workspaceId, memorySpaceId } = use(params);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const tabParam = searchParams.get("tab");
  const activeTab: TabValue =
    tabParam && VALID_TABS.includes(tabParam as TabValue)
      ? (tabParam as TabValue)
      : "sources";

  const setActiveTab = useCallback(
    (value: string | number | null) => {
      if (value === null) return;
      const tab = String(value);
      const params = new URLSearchParams(searchParams.toString());
      params.set("tab", tab);
      router.replace(`${pathname}?${params.toString()}`);
    },
    [router, pathname, searchParams]
  );

  const { data: workspace, isLoading: workspaceLoading } = useWorkspace(workspaceId);
  const { data: memorySpace, isLoading: memorySpaceLoading } = useMemorySpace(memorySpaceId);
  const { data: sourcesData } = useSources(memorySpaceId, { page: 1, page_size: 1 });
  const { data: recordsData } = useRecords(memorySpaceId, { page: 1, page_size: 1 });

  if (workspaceLoading || memorySpaceLoading) {
    return <PageSkeleton />;
  }

  const workspaceName = workspace?.name ?? "Workspace";
  const memorySpaceName = memorySpace?.name ?? "Memory Space";
  const isArchived = memorySpace?.status === "archived";

  const sourceCount = sourcesData?.total ?? 0;
  const recordCount = recordsData?.total ?? 0;

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

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="sources">
            <FileText className="h-4 w-4" />
            Sources ({sourceCount})
          </TabsTrigger>
          <TabsTrigger value="records">
            <ListChecks className="h-4 w-4" />
            Records ({recordCount})
          </TabsTrigger>
          <TabsTrigger value="summary">
            <ScrollText className="h-4 w-4" />
            Summary
          </TabsTrigger>
          <TabsTrigger value="ask">
            <Brain className="h-4 w-4" />
            Ask
          </TabsTrigger>
        </TabsList>

        <TabsContent value="sources">
          <SourceList memorySpaceId={memorySpaceId} />
        </TabsContent>

        <TabsContent value="records">
          <RecordList memorySpaceId={memorySpaceId} />
        </TabsContent>

        <TabsContent value="summary">
          <SummaryPanel memorySpaceId={memorySpaceId} />
        </TabsContent>

        <TabsContent value="ask">
          <QueryPanel memorySpaceId={memorySpaceId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
