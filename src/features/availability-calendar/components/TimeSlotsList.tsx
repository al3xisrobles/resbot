import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { SkeletonRect } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Clock } from "lucide-react";
import { useSlotsData } from "../api/useSlotsData";

interface TimeSlotsListProps {
    venueId: string | null;
    selectedDate: Date | undefined;
    partySize: string;
    resyLink: string | null;
    onTimeSlotSelect: (timeSlot: string) => void;
}

function TimeSlotsSkeleton() {
    return (
        <div className="space-y-2">
            {Array.from({ length: 6 }, (_, i) => (
                <SkeletonRect key={i} width="100%" height="40px" rounding="8" />
            ))}
        </div>
    );
}

function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <Clock className="size-12 text-muted-foreground mb-4" />
            <p className="text-sm font-medium text-foreground mb-1">
                Select a date to see available times
            </p>
            <p className="text-xs text-muted-foreground">
                Choose a date from the calendar to view reservation time slots
            </p>
        </div>
    );
}

function StatusMessage({ status }: { status: string }) {
    const getStatusMessage = () => {
        switch (status) {
            case "Sold out":
                return "This date is fully booked";
            case "Closed":
                return "The restaurant is closed on this day";
            case "Not released yet":
                return "Reservations for this date haven't been released yet";
            case "Resy temporarily unavailable":
                return "Unable to fetch availability at this time. Please try again later.";
            case "Unable to fetch":
                return "Unable to load time slots. Please try again.";
            default:
                return status;
        }
    };

    return (
        <Alert>
            <AlertDescription>{getStatusMessage()}</AlertDescription>
        </Alert>
    );
}

function TimeSlotButton({
    time,
    resyLink,
    onTimeSlotSelect,
}: {
    time: string;
    resyLink: string | null;
    onTimeSlotSelect: () => void;
}) {
    const handleClick = () => {
        // Update the selected time slot
        onTimeSlotSelect();
        // Open Resy link in new tab if available
        if (resyLink) {
            window.open(resyLink, "_blank");
        }
    };

    return (
        <Button
            variant="outline"
            className="w-full justify-center"
            onClick={handleClick}
        >
            {time}
        </Button>
    );
}

export function TimeSlotsList({
    venueId,
    selectedDate,
    partySize,
    resyLink,
    onTimeSlotSelect,
}: TimeSlotsListProps) {
    const { slotsData, loadingSlots, slotsError } = useSlotsData(
        venueId,
        selectedDate,
        partySize
    );

    // Empty state when no date is selected
    if (!selectedDate) {
        return <EmptyState />;
    }

    // Loading state
    if (loadingSlots) {
        return (
            <div className="space-y-4">
                <div className="w-full text-center">
                    <h3 className="text-lg font-semibold mb-1">
                        {format(selectedDate, "EEE, MMM d")}
                    </h3>
                    <p className="text-sm text-muted-foreground">Available times</p>
                </div>
                <TimeSlotsSkeleton />
            </div>
        );
    }

    // Error state
    if (slotsError) {
        return (
            <div className="space-y-4">
                <div>
                    <h3 className="text-lg font-semibold mb-1">
                        {format(selectedDate, "EEE, MMM d")}
                    </h3>
                    <p className="text-sm text-muted-foreground">Available times</p>
                </div>
                <Alert variant="destructive">
                    <AlertCircle className="size-4" />
                    <AlertDescription>{slotsError}</AlertDescription>
                </Alert>
            </div>
        );
    }

    // No slots data
    if (!slotsData) {
        return (
            <div className="space-y-4">
                <div>
                    <h3 className="text-lg font-semibold mb-1">
                        {format(selectedDate, "EEE, MMM d")}
                    </h3>
                    <p className="text-sm text-muted-foreground">Available times</p>
                </div>
                <EmptyState />
            </div>
        );
    }

    // Status message when no slots available
    if (slotsData.status) {
        return (
            <div className="space-y-4">
                <div>
                    <h3 className="text-lg font-semibold mb-1">
                        {format(selectedDate, "EEE, MMM d")}
                    </h3>
                    <p className="text-sm text-muted-foreground">Available times</p>
                </div>
                <StatusMessage status={slotsData.status} />
            </div>
        );
    }

    // Convert time string to timeSlot format (e.g., "7:00 PM" -> "19:0")
    const convertTimeToSlot = (timeStr: string): string => {
        try {
            const [time, period] = timeStr.split(" ");
            const [hour, minute] = time.split(":");
            let hour24 = parseInt(hour, 10);
            if (period === "PM" && hour24 !== 12) {
                hour24 += 12;
            } else if (period === "AM" && hour24 === 12) {
                hour24 = 0;
            }
            // Remove leading zero from minute to match format (e.g., "00" -> "0", "15" -> "15")
            const minuteNum = parseInt(minute, 10);
            return `${hour24}:${minuteNum}`;
        } catch {
            return "";
        }
    };

    // Deduplicate time slots (remove duplicates from different seating types)
    const uniqueTimes = Array.from(new Set(slotsData.times));

    // Display time slots
    return (
        <div className="space-y-4">
            <div>
                <h3 className="text-lg font-semibold mb-1">
                    {format(selectedDate, "EEE, MMM d")}
                </h3>
                <p className="text-sm text-muted-foreground">Available times</p>
            </div>
            {uniqueTimes.length === 0 ? (
                <Alert>
                    <AlertCircle className="size-4" />
                    <AlertDescription>No time slots available</AlertDescription>
                </Alert>
            ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                    {uniqueTimes.map((time, index) => {
                        const timeSlotValue = convertTimeToSlot(time);
                        return (
                            <TimeSlotButton
                                key={`${time}-${index}`}
                                time={time}
                                resyLink={resyLink}
                                onTimeSlotSelect={() => onTimeSlotSelect(timeSlotValue)}
                            />
                        );
                    })}
                </div>
            )}
        </div>
    );
}
