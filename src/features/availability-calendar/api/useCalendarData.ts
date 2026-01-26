import { useState, useEffect } from "react";
import { getCalendar } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { CalendarData } from "../lib/types";

export function useCalendarData(
  venueId: string | null,
  partySize: string
) {
  const auth = useAuth();
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [loadingCalendar, setLoadingCalendar] = useState(false);
  const [calendarError, setCalendarError] = useState<string | null>(null);

  useEffect(() => {
    if (!venueId) return;

    const fetchCalendarData = async () => {
      try {
        setLoadingCalendar(true);
        setCalendarError(null);
        const user = auth.currentUser;
        const data = await getCalendar(user!.uid, venueId, partySize);
        setCalendarData(data);
      } catch (err) {
        setCalendarError(
          err instanceof Error ? err.message : "Failed to load calendar"
        );
      } finally {
        setLoadingCalendar(false);
      }
    };

    fetchCalendarData();
  }, [venueId, partySize, auth.currentUser]);

  return {
    calendarData,
    loadingCalendar,
    calendarError,
  };
}
