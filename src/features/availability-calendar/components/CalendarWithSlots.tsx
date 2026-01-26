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

export function CalendarWithSlots({
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
                    reservationForm={reservationForm}
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
