import { useMemo, useCallback, memo } from "react";
import { format } from "date-fns";
import { Calendar, CalendarDayButton } from "@/components/ui/calendar";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import type { CalendarData } from "../lib/types";
import { CalendarDayButtonWithTooltip } from "./CalendarDayButton.private";

interface AvailabilityCalendarProps {
  calendarData: CalendarData | null;
  calendarError: string | null;
  selectedDate: Date | undefined;
  onDateSelect: (date: Date | undefined) => void;
}

function AvailabilityCalendarComponent({
  calendarData,
  calendarError,
  selectedDate,
  onDateSelect,
}: AvailabilityCalendarProps) {

  // Memoize the DayButton component to prevent remounting all days on every render
  const DayButtonComponent = useMemo(() => {
    if (!calendarData) return undefined;
    
    // Create a stable component that captures calendarData
    return function MemoizedDayButton(props: React.ComponentProps<typeof CalendarDayButton>) {
      return <CalendarDayButtonWithTooltip {...props} calendarData={calendarData} />;
    };
  }, [calendarData]);

  // Memoize disabled callback
  const disabledDates = useCallback(
    (date: Date) => {
      if (!calendarData) return true;
      const dateStr = format(date, "yyyy-MM-dd");
      const dateEntry = calendarData.availability.find((a) => a.date === dateStr);
      const dateAvailable = dateEntry ? !dateEntry.closed : false;
      return !dateAvailable;
    },
    [calendarData]
  );

  // Memoize modifiers
  const modifiers = useMemo(() => {
    if (!calendarData) return {};
    return {
      available: (date: Date) => {
        const dateStr = format(date, "yyyy-MM-dd");
        const dateAvailability = calendarData.availability.find((a) => a.date === dateStr);
        return dateAvailability?.available || false;
      },
      soldOut: (date: Date) => {
        const dateStr = format(date, "yyyy-MM-dd");
        const dateAvailability = calendarData.availability.find((a) => a.date === dateStr);
        return dateAvailability?.soldOut || false;
      },
    };
  }, [calendarData]);

  // Memoize components object
  const components = useMemo(() => {
    if (!DayButtonComponent) return undefined;
    return { DayButton: DayButtonComponent };
  }, [DayButtonComponent]);

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
      selected={selectedDate}
      onSelect={onDateSelect}
      disabled={disabledDates}
      modifiers={modifiers}
      modifiersClassNames={{
        available: "[&>button:not([data-selected-single=true])]:text-blue-600 [&>button:not([data-selected-single=true])]:font-bold",
        soldOut: "[&>button:not([data-selected-single=true])]:text-red-600",
      }}
      components={components}
    />
  );
}

// Memoize to prevent re-renders when unrelated props change
export const AvailabilityCalendar = memo(AvailabilityCalendarComponent, (prevProps, nextProps) => {
  return (
    prevProps.calendarData === nextProps.calendarData &&
    prevProps.calendarError === nextProps.calendarError &&
    prevProps.selectedDate === nextProps.selectedDate &&
    prevProps.onDateSelect === nextProps.onDateSelect
  );
});
