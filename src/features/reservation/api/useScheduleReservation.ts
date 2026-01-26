import { useState, useEffect } from "react";
import { format } from "date-fns";
import { toast } from "sonner";
import { scheduleReservationSnipe } from "@/services/firebase";
import { useAuth } from "@/contexts/AuthContext";
import type { ReservationFormState } from "../atoms/reservationFormAtom";

export function useScheduleReservation(
  venueId: string | null,
  reservationForm: ReservationFormState,
  reserveOnEmulation: boolean
) {
  const auth = useAuth();
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

    setLoadingSubmit(true);
    setError(null);

    try {
      // Parse time slot
      const [hour, minute] = reservationForm.timeSlot.split(":");
      const [dropHour, dropMinute] = reservationForm.dropTimeSlot.split(":");

      const user = auth.currentUser;

      // Convert drop date to EST timezone
      const dropDateInEst = new Date(
        reservationForm.dropDate.toLocaleString("en-US", {
          timeZone: "America/New_York",
        })
      );
      const dropDateFormatted = format(dropDateInEst, "yyyy-MM-dd");

      const { jobId, targetTimeIso } = await scheduleReservationSnipe({
        venueId,
        partySize: Number(reservationForm.partySize),
        date: format(reservationForm.date, "yyyy-MM-dd"),
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
        dropHour: Number(dropHour),
        dropMinute: Number(dropMinute),
        userId: user?.uid ?? null,
        actuallyReserve: reserveOnEmulation,
      });

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
