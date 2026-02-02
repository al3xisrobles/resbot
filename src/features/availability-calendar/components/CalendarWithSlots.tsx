import { memo } from "react";
import { AvailabilityCalendar } from "./AvailabilityCalendar";
import { TimeSlotsList } from "./TimeSlotsList";
import type { CalendarData } from "../lib/types";
import type { ReservationFormState } from "../../reservation/atoms/reservationFormAtom";

interface CalendarWithSlotsProps {
    calendarData: CalendarData | null;
    calendarError: string | null;
    reservationForm: ReservationFormState;
    venueId: string | null;
    resyLink: string | null;
    onDateSelect: (date: Date | undefined) => void;
    onTimeSlotSelect: (timeSlot: string) => void;
}

function CalendarWithSlotsComponent({
    calendarData,
    calendarError,
    reservationForm,
    venueId,
    resyLink,
    onDateSelect,
    onTimeSlotSelect,
}: CalendarWithSlotsProps) {

    return (
        <div className="flex gap-6 w-full">
            {/* Calendar */}
            <div className="flex-1 min-w-0">
                <AvailabilityCalendar
                    calendarData={calendarData}
                    calendarError={calendarError}
                    selectedDate={reservationForm.date}
                    onDateSelect={onDateSelect}
                />
            </div>

            {/* Time Slots List */}
            <div className="w-[120px] shrink-0">
                <TimeSlotsList
                    venueId={venueId}
                    selectedDate={reservationForm.date}
                    partySize={reservationForm.partySize}
                    resyLink={resyLink}
                    onTimeSlotSelect={onTimeSlotSelect}
                />
            </div>
        </div>
    );
}

// Memoize to prevent re-renders when dropSchedules change (only re-render when date/partySize changes)
export const CalendarWithSlots = memo(CalendarWithSlotsComponent, (prevProps, nextProps) => {
    // Only re-render if relevant props change
    return (
        prevProps.calendarData === nextProps.calendarData &&
        prevProps.calendarError === nextProps.calendarError &&
        prevProps.venueId === nextProps.venueId &&
        prevProps.resyLink === nextProps.resyLink &&
        prevProps.reservationForm.date === nextProps.reservationForm.date &&
        prevProps.reservationForm.partySize === nextProps.reservationForm.partySize &&
        // Ignore dropSchedules changes
        prevProps.onDateSelect === nextProps.onDateSelect &&
        prevProps.onTimeSlotSelect === nextProps.onTimeSlotSelect
    );
});
