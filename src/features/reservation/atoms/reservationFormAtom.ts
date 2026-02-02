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
});
