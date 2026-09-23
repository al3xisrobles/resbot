import type { Reservation as BaseReservation } from "@/lib/interfaces/app-types";

export interface Reservation extends BaseReservation {
  /** True for a cancellation watch (books the first opening in [rangeStart, rangeEnd]) */
  watchMode?: boolean;
  rangeStart?: string; // "HH:MM" - earliest acceptable time (watch only)
  rangeEnd?: string; // "HH:MM" - latest acceptable time (watch only)
}
