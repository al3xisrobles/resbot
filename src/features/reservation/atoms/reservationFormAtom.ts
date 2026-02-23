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
});
