import { UserPageLayout } from "@/common/components/UserPageLayout";

export function BookmarkedRestaurantsPage() {
  return (
    <UserPageLayout
      title="Bookmarked Restaurants"
      description="Your bookmarked restaurants will appear here"
    >
      <div className="flex items-center justify-center h-[400px]">
        <div className="text-center space-y-3">
          <p className="text-muted-foreground">
            Your bookmarked restaurants will appear here
          </p>
        </div>
      </div>
    </UserPageLayout>
  );
}
