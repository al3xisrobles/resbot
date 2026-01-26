import { format } from "date-fns";
import { CalendarDayButton } from "@/components/ui/calendar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { CalendarData } from "../lib/types";

/**
 * Custom calendar day button with tooltip
 * This is a private component only used within the availability-calendar feature
 */
export function CalendarDayButtonWithTooltip({
  day,
  modifiers,
  calendarData,
  ...props
}: React.ComponentProps<typeof CalendarDayButton> & {
  calendarData: CalendarData;
}) {
  const getTooltipText = (): string => {
    const dateStr = format(day.date, "yyyy-MM-dd");
    const dateEntry = calendarData.availability.find(
      (a) => a.date === dateStr
    );

    if (!dateEntry) {
      return "Reservations not yet released";
    }

    if (dateEntry.closed) {
      return "Restaurant is closed this day";
    }

    if (dateEntry.soldOut) {
      return "Fully booked - no availability";
    }

    if (dateEntry.available) {
      return "Available for reservations";
    }

    return "Reservations not yet released";
  };

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <CalendarDayButton day={day} modifiers={modifiers} {...props} />
      </TooltipTrigger>
      <TooltipContent>
        <p>{getTooltipText()}</p>
      </TooltipContent>
    </Tooltip>
  );
}
