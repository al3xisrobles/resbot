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

                if (!user) {
                    throw new Error("User not authenticated. Please log in.");
                }

                const dateStr = format(date, "yyyy-MM-dd");
                const data = await getSlots(user.uid, venueId, dateStr, partySize);
                setSlotsData(data);
            } catch (err) {
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
