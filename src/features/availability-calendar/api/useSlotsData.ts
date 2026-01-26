import { useState, useEffect } from "react";
import { format } from "date-fns";
import { getSlots } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export interface SlotsData {
    times: string[];
    status: string | null;
}

export function useSlotsData(
    venueId: string | null,
    date: Date | undefined,
    partySize: string
) {
    const auth = useAuth();
    const [slotsData, setSlotsData] = useState<SlotsData | null>(null);
    const [loadingSlots, setLoadingSlots] = useState(false);
    const [slotsError, setSlotsError] = useState<string | null>(null);

    useEffect(() => {
        if (!venueId || !date) {
            setSlotsData(null);
            setSlotsError(null);
            return;
        }

        const fetchSlotsData = async () => {
            try {
                setLoadingSlots(true);
                setSlotsError(null);
                const user = auth.currentUser;

                // Add logging before the call
                console.log("[useSlotsData] Starting fetch:", {
                    venueId,
                    date: format(date, "yyyy-MM-dd"),
                    partySize,
                    hasUser: !!user,
                    userId: user?.uid,
                });

                if (!user) {
                    const error = new Error("User not authenticated. Please log in.");
                    console.error("[useSlotsData] No user:", error);
                    throw error;
                }

                const dateStr = format(date, "yyyy-MM-dd");
                const data = await getSlots(user.uid, venueId, dateStr, partySize);
                setSlotsData(data);

                console.log("[useSlotsData] Successfully fetched slots:", data);
            } catch (err) {
                // Enhanced error logging
                console.error("[useSlotsData] Error fetching slots:", {
                    error: err,
                    errorMessage: err instanceof Error ? err.message : String(err),
                    errorStack: err instanceof Error ? err.stack : undefined,
                    errorName: err instanceof Error ? err.name : typeof err,
                    venueId,
                    date: date ? format(date, "yyyy-MM-dd") : null,
                    partySize,
                    hasUser: !!auth.currentUser,
                    userId: auth.currentUser?.uid,
                });

                setSlotsError(
                    err instanceof Error ? err.message : "Failed to load time slots"
                );
                setSlotsData(null);
            } finally {
                setLoadingSlots(false);
            }
        };

        fetchSlotsData();
    }, [venueId, date, partySize, auth.currentUser]);

    return {
        slotsData,
        loadingSlots,
        slotsError,
    };
}
