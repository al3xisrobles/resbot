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

  // Reset reservationScheduled when venue changes
  // Note: We intentionally don't reset on reservationForm changes to avoid
  // unnecessary state updates during form editing
  useEffect(() => {
    setReservationScheduled(false);
  }, [venueId]);

  const scheduleReservation = async () => {
    if (!venueId) {
      setError("No venue ID available");
      return;
    }

    if (!reservationForm.date) {
      setError("Please select a reservation date");
      return;
    }

    if (!reservationForm.dropSchedules || reservationForm.dropSchedules.length === 0) {
      setError("Please add at least one drop schedule");
      return;
    }

    // Validate all drop schedules
    for (const schedule of reservationForm.dropSchedules) {
      if (!schedule.dropDate) {
        setError("Please select a drop date for all schedules");
        return;
      }

      // Parse drop time
      const [dropHour, dropMinute] = schedule.dropTimeSlot.split(":").map(Number);

      // Validate drop time is in the future
      const dropDateTime = new Date(
        schedule.dropDate.getFullYear(),
        schedule.dropDate.getMonth(),
        schedule.dropDate.getDate(),
        dropHour,
        dropMinute
      );

      if (dropDateTime <= new Date()) {
        setError("All drop times must be in the future");
        return;
      }
    }

    setLoadingSubmit(true);
    setError(null);

    try {
      // Parse time slot
      const [hour, minute] = reservationForm.timeSlot.split(":");

      const user = auth.currentUser;

      // Format reservation date using local components (not UTC) to avoid timezone shifts
      const reservationDateFormatted = `${reservationForm.date.getFullYear()}-${String(reservationForm.date.getMonth() + 1).padStart(2, '0')}-${String(reservationForm.date.getDate()).padStart(2, '0')}`;

      // Schedule a reservation for each drop schedule
      const jobIds: string[] = [];
      const errors: string[] = [];

      for (const schedule of reservationForm.dropSchedules) {
        // Skip schedules without a drop date (shouldn't happen due to validation, but TypeScript needs this)
        if (!schedule.dropDate) {
          continue;
        }

        try {
          // Format drop date as YYYY-MM-DD using the date's local components (not UTC)
          const dropDateFormatted = `${schedule.dropDate.getFullYear()}-${String(schedule.dropDate.getMonth() + 1).padStart(2, '0')}-${String(schedule.dropDate.getDate()).padStart(2, '0')}`;

          // Parse drop time
          const [dropHour, dropMinute] = schedule.dropTimeSlot.split(":").map(Number);

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
          console.log("[useScheduleReservation] Drop date from form:", schedule.dropDate?.toISOString());
          console.log("[useScheduleReservation] City timezone:", cityTimezone);

          const { jobId } = await scheduleReservationSnipe(requestPayload);
          jobIds.push(jobId);
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : "Failed to schedule reservation";
          errors.push(errorMessage);
          console.error("[useScheduleReservation] Error scheduling reservation:", err);
        }
      }

      // Show success or error messages
      if (jobIds.length > 0) {
        const successMessage = jobIds.length === 1
          ? `Reservation Scheduled! Job ID: ${jobIds[0]}`
          : `${jobIds.length} Reservations Scheduled! Job IDs: ${jobIds.join(", ")}`;
        
        toast.success("Reservation Scheduled!", {
          description: successMessage,
          className: "bg-green-600 text-white border-green-600",
          position: "bottom-right",
        });
      }

      if (errors.length > 0) {
        const errorMessage = errors.length === 1
          ? errors[0]
          : `${errors.length} schedules failed: ${errors.join("; ")}`;
        setError(errorMessage);
        toast.error("Some reservations failed to schedule", {
          description: errorMessage,
        });
      }

      // Only mark as scheduled if at least one succeeded
      if (jobIds.length > 0) {
        setReservationScheduled(true);
      }
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
