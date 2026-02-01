import { useState, useEffect } from "react";
import { toast } from "sonner";
import { useAtom } from "jotai";
import { scheduleReservationSnipe } from "@/services/firebase";
import { useAuth } from "@/contexts/AuthContext";
import { cityTimezoneAtom } from "@/atoms/cityAtom";
import type { ReservationFormState } from "../atoms/reservationFormAtom";

export function useScheduleReservation(
  venueId: string | null,
  reservationForm: ReservationFormState,
  reserveOnEmulation: boolean
) {
  const auth = useAuth();
  const [cityTimezone] = useAtom(cityTimezoneAtom);
  const [loadingSubmit, setLoadingSubmit] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reservationScheduled, setReservationScheduled] = useState(false);

  // Reset reservationScheduled when form state or venue changes
  useEffect(() => {
    setReservationScheduled(false);
  }, [reservationForm, venueId]);

  const scheduleReservation = async () => {
    if (!venueId) {
      setError("No venue ID available");
      return;
    }

    if (!reservationForm.date) {
      setError("Please select a reservation date");
      return;
    }

    if (!reservationForm.dropDate) {
      setError("Please select a drop date");
      return;
    }

    // Parse drop time
    const [dropHour, dropMinute] = reservationForm.dropTimeSlot.split(":").map(Number);

    // Validate drop time is in the future
    const dropDateTime = new Date(
      reservationForm.dropDate.getFullYear(),
      reservationForm.dropDate.getMonth(),
      reservationForm.dropDate.getDate(),
      dropHour,
      dropMinute
    );

    if (dropDateTime <= new Date()) {
      setError("Drop time must be in the future");
      return;
    }

    setLoadingSubmit(true);
    setError(null);

    try {
      // Parse time slot
      const [hour, minute] = reservationForm.timeSlot.split(":");

      const user = auth.currentUser;

      // Format dates as YYYY-MM-DD using the date's local components (not UTC)
      // This ensures Jan 27 selected in the calendar is sent as "2026-01-27" regardless of timezone
      const dropDateFormatted = `${reservationForm.dropDate.getFullYear()}-${String(reservationForm.dropDate.getMonth() + 1).padStart(2, '0')}-${String(reservationForm.dropDate.getDate()).padStart(2, '0')}`;

      // Format reservation date using local components (not UTC) to avoid timezone shifts
      const reservationDateFormatted = `${reservationForm.date.getFullYear()}-${String(reservationForm.date.getMonth() + 1).padStart(2, '0')}-${String(reservationForm.date.getDate()).padStart(2, '0')}`;

      const requestPayload = {
        venueId,
        partySize: Number(reservationForm.partySize),
        date: reservationDateFormatted,
        dropDate: dropDateFormatted,
        hour: Number(hour),
        minute: Number(minute),
        windowHours: reservationForm.windowHours
          ? Number(reservationForm.windowHours)
          : undefined,
        seatingType:
          reservationForm.seatingType === "any"
            ? undefined
            : reservationForm.seatingType,
        dropHour,
        dropMinute,
        userId: user?.uid ?? null,
        actuallyReserve: reserveOnEmulation,
        timezone: cityTimezone, // Pass the city's timezone to the backend
      };

      // Log the request for debugging
      console.log("[useScheduleReservation] Scheduling with payload:", requestPayload);
      console.log("[useScheduleReservation] Drop date from form:", reservationForm.dropDate?.toISOString());
      console.log("[useScheduleReservation] City timezone:", cityTimezone);

      const { jobId } = await scheduleReservationSnipe(requestPayload);

      // Show success toast with green background
      toast.success("Reservation Scheduled!", {
        description: `Job ID: ${jobId}`,
        className: "bg-green-600 text-white border-green-600",
        position: "bottom-right",
      });

      setReservationScheduled(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to make reservation"
      );
      toast.error("Failed to schedule reservation", {
        description: err instanceof Error ? err.message : "An error occurred",
      });
    } finally {
      setLoadingSubmit(false);
    }
  };

  return {
    scheduleReservation,
    loadingSubmit,
    error,
    reservationScheduled,
  };
}
