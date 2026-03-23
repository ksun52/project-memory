import { PageHeader } from "@/shared/components/page-header";
import { Breadcrumbs } from "@/shared/components/breadcrumbs";

export default function WorkspacesPage() {
  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Workspaces" }]} />
      <PageHeader
        title="Workspaces"
        description="Manage your project workspaces"
      />
      <p className="text-muted-foreground">
        Workspace list coming in Track E.
      </p>
    </div>
  );
}
