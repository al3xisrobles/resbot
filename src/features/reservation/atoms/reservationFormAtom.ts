import { atom } from "jotai";

export interface DropSchedule {
  id: string; // Unique ID for stable React keys
  dropDate: Date | undefined;
  dropTimeSlot: string;
}

export interface ReservationFormState {
  partySize: string;
  date: Date | undefined;
  timeSlot: string;
  windowHours: string;
  seatingType: string;
  dropSchedules: DropSchedule[];
  /** When true, poll around drop time to discover when slots actually appear */
  discoveryMode: boolean;
  /** Minutes before expected drop to start polling (discovery mode) */
  windowBeforeMinutes: string;
  /** Minutes after expected drop to keep polling (discovery mode) */
  windowAfterMinutes: string;
  /** When true, watch for cancellations inside [rangeStart, rangeEnd] instead of sniping a drop */
  watchMode: boolean;
  /** Earliest acceptable time (watch mode), as a TIME_SLOTS value like "17:0" */
  rangeStart: string;
  /** Latest acceptable time (watch mode), as a TIME_SLOTS value like "21:0" */
  rangeEnd: string;
}

function slotToMinutes(slot: string): number {
  const [hour, minute] = slot.split(":").map(Number);
  return hour * 60 + minute;
}

/** Converts a TIME_SLOTS value ("17:0") to the "HH:MM" string the backend expects ("17:00"). */
export function slotToHHMM(slot: string): string {
  const [hour, minute] = slot.split(":").map(Number);
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

/** A watch range is valid when the latest time is not before the earliest (both ends inclusive). */
export function isWatchRangeValid(rangeStart: string, rangeEnd: string): boolean {
  return slotToMinutes(rangeEnd) >= slotToMinutes(rangeStart);
}

/**
 * Jotai atom for reservation form state.
 * This persists reservation form data across navigation.
 */
export const reservationFormAtom = atom<ReservationFormState>({
  partySize: "2",
  date: undefined,
  timeSlot: "19:0", // Default to 7:00 PM
  windowHours: "1",
  seatingType: "any",
  dropSchedules: [
    {
      id: crypto.randomUUID(),
      dropDate: undefined,
      dropTimeSlot: "9:0", // Default to 9:00 AM
    },
  ],
  discoveryMode: false,
  windowBeforeMinutes: "30",
  windowAfterMinutes: "30",
  watchMode: false,
  rangeStart: "17:0", // Default to 5:00 PM
  rangeEnd: "21:0", // Default to 9:00 PM
});
