import { useState, useEffect, useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ReservationsDataTable } from "@/components/ReservationsDataTable";
import {
  getUserReservationJobs,
  type ReservationJob,
  getVenueCache,
} from "@/services/firebase";
import { auth } from "@/services/firebase";
import { searchRestaurant } from "@/lib/api";
import type { Reservation } from "@/lib/mockReservations";

/**
 * Transform Firestore ReservationJob to UI Reservation format
 */
function transformJobToReservation(
  job: ReservationJob,
  venueName: string,
  venueImage: string
): Reservation {
  // Map Firestore status to UI status
  let status: Reservation["status"];
  if (job.status === "pending") {
    status = "Scheduled";
  } else if (job.status === "done") {
    status = "Succeeded";
  } else {
    // 'failed' or 'error' both map to 'Failed'
    status = "Failed";
  }

  // Format time from hour/minute
  const time = `${String(job.hour).padStart(2, "0")}:${String(
    job.minute
  ).padStart(2, "0")}`;

  // Get attemptedAt timestamp from lastUpdate
  const attemptedAt = job.lastUpdate?.toMillis?.() || undefined;

  // Use errorMessage for failed jobs
  const note =
    job.status === "error" && job.errorMessage ? job.errorMessage : undefined;

  return {
    id: job.jobId,
    venueId: job.venueId,
    venueName,
    venueImage,
    date: job.date,
    time,
    partySize: job.partySize,
    status,
    attemptedAt,
    note,
  };
}

export function ReservationsPage() {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReservations = async () => {
      const user = auth.currentUser;
      if (!user) {
        console.log("[ReservationsPage] No user logged in");
        setLoading(false);
        return;
      }

      try {
        console.log(
          "[ReservationsPage] Fetching reservation jobs for user:",
          user.uid
        );
        const jobs = await getUserReservationJobs(user.uid);
        console.log("[ReservationsPage] Found jobs:", jobs);

        // Transform Firestore jobs to Reservation format
        const reservationsWithVenues = await Promise.all(
          jobs.map(async (job) => {
            // Try to get venue name from cache or API
            let venueName = "Unknown Restaurant";
            let venueImage = "";

            try {
              const venueData = await searchRestaurant(job.venueId);
              venueName = venueData.name;

              // Try to get image from cache
              const cachedVenue = await getVenueCache(job.venueId);
              if (cachedVenue?.photoUrl) {
                venueImage = cachedVenue.photoUrl;
              } else if (
                cachedVenue?.photoUrls &&
                cachedVenue.photoUrls.length > 0
              ) {
                venueImage = cachedVenue.photoUrls[0];
              }
            } catch (error) {
              console.error(
                `[ReservationsPage] Failed to fetch venue ${job.venueId}:`,
                error
              );
            }

            return transformJobToReservation(job, venueName, venueImage);
          })
        );

        setReservations(reservationsWithVenues);
      } catch (error) {
        console.error("[ReservationsPage] Error fetching reservations:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchReservations();
  }, []);

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
      <div className="min-h-screen bg-background pt-24">
        <main className="container mx-auto px-4 py-8 max-w-240">
          <div className="text-center py-8 text-muted-foreground">
            Loading reservations...
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pt-24">
      <main className="container mx-auto px-4 py-8 max-w-240">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">
            Reservations
          </h1>
          <p className="text-muted-foreground">
            Manage your restaurant booking attempts and reservations
          </p>
        </div>

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
            <ReservationsDataTable reservations={scheduledReservations} />
          </TabsContent>

          <TabsContent value="succeeded">
            <ReservationsDataTable reservations={succeededReservations} />
          </TabsContent>

          <TabsContent value="failed">
            <ReservationsDataTable reservations={failedReservations} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
