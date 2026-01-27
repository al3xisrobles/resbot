import { useState } from "react";

import { ProfileTab } from "@/features/profile/ProfileTab";
import { ProfileTabSkeleton } from "@/features/profile/ProfileTabSkeleton";
import { ResyAccountTab } from "@/features/profile/ResyAccountTab";
import { ResyAccountTabSkeleton } from "@/features/profile/ResyAccountTabSkeleton";
import { UserPageLayout } from "@/common/components/UserPageLayout";
import { cn } from "@/lib/utils";
import { User, CreditCard } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

type Tab = "profile" | "resy";

export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const [resyTabLoading, setResyTabLoading] = useState(true);
  const { currentUser } = useAuth();

  const tabs: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
    { id: "profile", label: "Profile", icon: <User className="h-4 w-4" /> },
    {
      id: "resy",
      label: "Resy Account",
      icon: <CreditCard className="h-4 w-4" />,
    },
  ];

  return (
    <UserPageLayout
      title="Settings"
      description="Manage your account settings and preferences"
    >
      <div className="flex flex-col md:flex-row gap-8">
        {/* Left Sidebar - Vertical Tabs */}
        <aside className="w-full md:w-64 shrink-0 border-b md:border-b-0 pb-4 md:pb-0 md:pr-8">
          <nav className="flex md:flex-col gap-1 overflow-x-auto md:overflow-x-visible">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  if (tab.id === "resy") {
                    setResyTabLoading(true);
                  }
                }}
                className={cn(
                  "flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap",
                  activeTab === tab.id
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Right Content Area */}
        <main className="flex-1 min-w-0">
          {activeTab === "profile" && (
            currentUser ? <ProfileTab /> : <ProfileTabSkeleton />
          )}
          {activeTab === "resy" && (
            <>
              {resyTabLoading && <ResyAccountTabSkeleton />}
              <div style={{ display: resyTabLoading ? "none" : "block" }}>
                <ResyAccountTab onLoadingChange={setResyTabLoading} key="resy-tab" />
              </div>
            </>
          )}
        </main>
      </div>
    </UserPageLayout>
  );
}
