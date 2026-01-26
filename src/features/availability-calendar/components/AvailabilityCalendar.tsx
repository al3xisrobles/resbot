import { format } from "date-fns";
import { Calendar } from "@/components/ui/calendar";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import type { CalendarData } from "../lib/types";
import { CalendarDayButtonWithTooltip } from "./CalendarDayButton.private";
import type { ReservationFormState } from "../../reservation/atoms/reservationFormAtom";

interface AvailabilityCalendarProps {
  calendarData: CalendarData | null;
  calendarError: string | null;
  reservationForm: ReservationFormState;
  onDateSelect: (date: Date | undefined) => void;
}

export function AvailabilityCalendar({
  calendarData,
  calendarError,
  reservationForm,
  onDateSelect,
}: AvailabilityCalendarProps) {
  if (calendarError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="size-4" />
        <AlertDescription>{calendarError}</AlertDescription>
      </Alert>
    );
  }

  if (!calendarData) {
    return null;
  }

  return (
    <Calendar
      mode="single"
      className="w-full rounded-lg border shadow-sm [--cell-size:--spacing(10.5)]"
      selected={reservationForm.date}
      onSelect={onDateSelect}
      disabled={(date) => {
        const dateStr = format(date, "yyyy-MM-dd");
        const dateEntry = calendarData.availability.find(
          (a) => a.date === dateStr
        );
        const dateAvailable = dateEntry ? !dateEntry.closed : false;
        return !dateAvailable;
      }}
      modifiers={{
        available: (date) => {
          const dateStr = format(date, "yyyy-MM-dd");
          const dateAvailability = calendarData.availability.find(
            (a) => a.date === dateStr
          );
          return dateAvailability?.available || false;
        },
        soldOut: (date) => {
          const dateStr = format(date, "yyyy-MM-dd");
          const dateAvailability = calendarData.availability.find(
            (a) => a.date === dateStr
          );
          return dateAvailability?.soldOut || false;
        },
      }}
      modifiersClassNames={{
        available: "[&>button:not([data-selected-single=true])]:text-blue-600 [&>button:not([data-selected-single=true])]:font-bold",
        soldOut: "[&>button:not([data-selected-single=true])]:text-red-600",
      }}
      components={{
        DayButton: (props) => (
          <CalendarDayButtonWithTooltip {...props} calendarData={calendarData} />
        ),
      }}
    />
  );
}
