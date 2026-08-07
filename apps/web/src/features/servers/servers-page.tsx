import { servers } from "@/mocks/data";
import { AddServerDialog } from "@/components/server/add-server-dialog";
import { ServerTable } from "@/components/server/server-table";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { SectionPanel } from "@/components/shared/section-panel";

export function ServersPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Servers"
        description="Manage local lab nodes and cloud GPU hosts from one inventory."
        actions={<AddServerDialog />}
      />
      <SectionPanel
        title="Server inventory"
        description="Search, filter, sort, and inspect registered infrastructure"
      >
        <ServerTable data={servers} />
      </SectionPanel>
    </PageContainer>
  );
}
