import { useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ReservationsDataTable } from "@/features/reservations/components/ReservationsDataTable";
import { ReservationsDataTableSkeleton } from "@/features/reservations/components/ReservationsDataTableSkeleton";
import { useReservationsData } from "@/features/reservations/api/useReservationsData";
import { UserPageLayout } from "@/common/components/UserPageLayout";

export function ReservationsPage() {
  const { reservations, loading, refetch } = useReservationsData();

  const scheduledReservations = useMemo(
    () => reservations.filter((r) => r.status === "Scheduled"),
    [reservations]
  );

  const succeededReservations = useMemo(
    () => reservations.filter((r) => r.status === "Succeeded"),
    [reservations]
  );

  const failedReservations = useMemo(
    () => reservations.filter((r) => r.status === "Failed"),
    [reservations]
  );

  if (loading) {
    return (
      <UserPageLayout
        title="Reservations"
        description="Manage your restaurant booking attempts and reservations"
      >
        <Tabs defaultValue="scheduled" className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="scheduled" className="w-max">
              Upcoming Attempts
              <span className="ml-2 px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-xs font-medium">
                0
              </span>
            </TabsTrigger>
            <TabsTrigger value="succeeded" className="w-max">
              Succeeded
              <span className="ml-2 px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-xs font-medium">
                0
              </span>
            </TabsTrigger>
            <TabsTrigger value="failed" className="w-max">
              Failed
              <span className="ml-2 px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900 text-xs font-medium">
                0
              </span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="scheduled">
            <ReservationsDataTableSkeleton />
          </TabsContent>

          <TabsContent value="succeeded">
            <ReservationsDataTableSkeleton />
          </TabsContent>

          <TabsContent value="failed">
            <ReservationsDataTableSkeleton />
          </TabsContent>
        </Tabs>
      </UserPageLayout>
    );
  }

  return (
    <UserPageLayout
      title="Reservations"
      description="Manage your restaurant booking attempts and reservations"
    >
      <Tabs defaultValue="scheduled" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="scheduled" className="w-max">
            Upcoming Attempts
            <span className="ml-2 px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-xs font-medium">
              {scheduledReservations.length}
            </span>
          </TabsTrigger>
          <TabsTrigger value="succeeded" className="w-max">
            Succeeded
            <span className="ml-2 px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-xs font-medium">
              {succeededReservations.length}
            </span>
          </TabsTrigger>
          <TabsTrigger value="failed" className="w-max">
            Failed
            <span className="ml-2 px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900 text-xs font-medium">
              {failedReservations.length}
            </span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="scheduled">
          <ReservationsDataTable reservations={scheduledReservations} onRefetch={refetch} />
        </TabsContent>

        <TabsContent value="succeeded">
          <ReservationsDataTable reservations={succeededReservations} onRefetch={refetch} />
        </TabsContent>

        <TabsContent value="failed">
          <ReservationsDataTable reservations={failedReservations} onRefetch={refetch} />
        </TabsContent>
      </Tabs>
    </UserPageLayout>
  );
}
