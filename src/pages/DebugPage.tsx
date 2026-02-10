import { UserPageLayout } from "@/common/components/UserPageLayout";
import { DebugDashboard } from "@/features/debug/components/DebugDashboard";

export function DebugPage() {
  return (
    <UserPageLayout
      title="Resy API Debug Dashboard"
      description="Probe Resy endpoints and inspect responses, schema validation, and rate limits."
    >
      <DebugDashboard />
    </UserPageLayout>
  );
}
