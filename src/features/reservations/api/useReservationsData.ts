import { useState, useEffect } from "react";
import {
    getUserReservationJobs,
    type ReservationJob,
    getVenueCache,
} from "@/services/firebase";
import { searchRestaurant, getSnipeLogsSummary } from "@/lib/api";
import type { Reservation } from "../lib/types";
import { useAuth } from "@/contexts/AuthContext";

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

    // Use errorMessage for failed jobs (both "error" and "failed" statuses)
    const note =
        (job.status === "error" || job.status === "failed") && job.errorMessage
            ? job.errorMessage
            : undefined;

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
        snipeTime: job.targetTimeIso,
        aiSummary: job.aiSummary,
    };
}

export function useReservationsData() {
    const [reservations, setReservations] = useState<Reservation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const auth = useAuth();

    useEffect(() => {
        const fetchReservations = async () => {
            const user = auth.currentUser;
            if (!user) {
                console.log("[useReservationsData] No user logged in");
                setLoading(false);
                return;
            }

            try {
                console.log(
                    "[useReservationsData] Fetching reservation jobs for user:",
                    user.uid
                );
                const jobs = await getUserReservationJobs(user.uid);
                console.log("[useReservationsData] Found jobs:", jobs);

                // Transform Firestore jobs to Reservation format
                const reservationsWithVenues = await Promise.all(
                    jobs.map(async (job) => {
                        // Try to get venue name from cache or API
                        let venueName = "Unknown Restaurant";
                        let venueImage = "";

                        try {
                            const user = auth.currentUser;
                            const venueData = await searchRestaurant(user!.uid, job.venueId);
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
                                `[useReservationsData] Failed to fetch venue ${job.venueId}:`,
                                error
                            );
                        }

                        return transformJobToReservation(job, venueName, venueImage);
                    })
                );

                setReservations(reservationsWithVenues);
                setError(null);
            } catch (error) {
                console.error("[useReservationsData] Error fetching reservations:", error);
                setError(
                    error instanceof Error ? error.message : "Failed to fetch reservations"
                );
            } finally {
                setLoading(false);
            }
        };

        fetchReservations();
    }, [auth.currentUser]);

    // Fetch AI summaries for failed reservations that don't have one yet
    useEffect(() => {
        const fetchMissingSummaries = async () => {
            const failedReservations = reservations.filter(
                (r) => r.status === "Failed" && !r.aiSummary
            );

            if (failedReservations.length === 0) return;

            // Fetch summaries for all failed reservations without summaries
            const summaryPromises = failedReservations.map(async (reservation) => {
                try {
                    const summary = await getSnipeLogsSummary(reservation.id);
                    return { id: reservation.id, summary };
                } catch (error) {
                    console.error(
                        `[useReservationsData] Failed to fetch summary for ${reservation.id}:`,
                        error
                    );
                    return null;
                }
            });

            const summaries = await Promise.all(summaryPromises);

            // Update reservations with summaries only if we got new data
            const hasNewSummaries = summaries.some((s) => s !== null);
            if (hasNewSummaries) {
                setReservations((prev) =>
                    prev.map((res) => {
                        const summaryData = summaries.find((s) => s?.id === res.id);
                        if (summaryData && !res.aiSummary) {
                            return { ...res, aiSummary: summaryData.summary };
                        }
                        return res;
                    })
                );
            }
        };

        if (reservations.length > 0 && !loading) {
            fetchMissingSummaries();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [reservations.length, loading]);

    return {
        reservations,
        loading,
        error,
    };
}
