import * as React from "react";
import { format } from "date-fns";
import { ChevronDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Button } from "@/components/ui/button";

interface UnifiedSearchControlsProps {
    /** Party size value */
    partySize: string;
    onPartySizeChange: (value: string) => void;
    /** Selected date */
    date?: Date;
    onDateChange: (date: Date | undefined) => void;
    /** Time slot value */
    timeSlot: string;
    onTimeSlotChange: (value: string) => void;
    /** Time slots options */
    timeSlots: Array<{ value: string; display: string }>;
    /** Optional click handler for the search button */
    onSearch?: () => void;
    /** Show search button */
    showSearchButton?: boolean;
    /** Disabled state */
    disabled?: boolean;
    /** Custom class name */
    className?: string;
}

function UnifiedSearchControls({
    partySize,
    onPartySizeChange,
    date,
    onDateChange,
    timeSlot,
    onTimeSlotChange,
    timeSlots,
    onSearch,
    showSearchButton = true,
    disabled = false,
    className,
}: UnifiedSearchControlsProps) {
    const [partySizeOpen, setPartySizeOpen] = React.useState(false);
    const [dateOpen, setDateOpen] = React.useState(false);
    const [timeOpen, setTimeOpen] = React.useState(false);

    const partySizeDisplay = partySize
        ? `${partySize} ${parseInt(partySize) === 1 ? "guest" : "guests"}`
        : "Guests";

    const dateDisplay = date ? format(date, "MMM d") : "Date";

    const timeDisplay =
        timeSlots.find((slot) => slot.value === timeSlot)?.display || "Time";

    // Common styles for trigger buttons
    const triggerButtonStyles =
        "flex items-center gap-1.5 px-5 py-3 text-sm font-medium hover:bg-accent/40 transition-colors cursor-pointer whitespace-nowrap";

    // Common styles for dropdown option buttons
    const optionButtonStyles =
        "flex items-center w-full px-3 py-2 text-sm rounded-md hover:bg-accent cursor-pointer transition-colors text-left";

    return (
        <div
            className={cn(
                "inline-flex items-center bg-background border rounded-full shadow-sm hover:shadow-md transition-shadow",
                disabled && "opacity-50 pointer-events-none",
                className
            )}
        >
            {/* Party Size Section */}
            <Popover open={partySizeOpen && !disabled} onOpenChange={(open) => !disabled && setPartySizeOpen(open)}>
                <PopoverTrigger asChild>
                    <button
                        type="button"
                        disabled={disabled}
                        className={cn(triggerButtonStyles, "rounded-l-full", disabled && "cursor-not-allowed")}
                    >
                        <span className={cn(!partySize && "text-muted-foreground")}>
                            {partySizeDisplay}
                        </span>
                        <ChevronDown className="size-3.5 text-muted-foreground" />
                    </button>
                </PopoverTrigger>
                <PopoverContent className="w-40 p-1" align="start">
                    <div className="flex flex-col">
                        {Array.from({ length: 6 }, (_, i) => i + 1).map((size) => (
                            <button
                                key={size}
                                type="button"
                                onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    onPartySizeChange(size.toString());
                                    setPartySizeOpen(false);
                                }}
                                className={cn(
                                    optionButtonStyles,
                                    partySize === size.toString() && "bg-accent"
                                )}
                            >
                                {size} {size === 1 ? "guest" : "guests"}
                            </button>
                        ))}
                    </div>
                </PopoverContent>
            </Popover>

            {/* Divider */}
            <div className="w-px h-6 bg-border" />

            {/* Date Section */}
            <Popover open={dateOpen && !disabled} onOpenChange={(open) => !disabled && setDateOpen(open)}>
                <PopoverTrigger asChild>
                    <button type="button" disabled={disabled} className={cn(triggerButtonStyles, disabled && "cursor-not-allowed")}>
                        <span className={cn(!date && "text-muted-foreground")}>
                            {dateDisplay}
                        </span>
                        <ChevronDown className="size-3.5 text-muted-foreground" />
                    </button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="center">
                    <Calendar
                        mode="single"
                        selected={date}
                        onSelect={(newDate) => {
                            onDateChange(newDate);
                            setDateOpen(false);
                        }}
                        disabled={(d) => d < new Date(new Date().setHours(0, 0, 0, 0))}
                    />
                </PopoverContent>
            </Popover>

            {/* Divider */}
            <div className="w-px h-6 bg-border" />

            {/* Time Section */}
            <Popover open={timeOpen && !disabled} onOpenChange={(open) => !disabled && setTimeOpen(open)}>
                <PopoverTrigger asChild>
                    <button
                        type="button"
                        disabled={disabled}
                        className={cn(
                            triggerButtonStyles,
                            !showSearchButton && "rounded-r-full",
                            disabled && "cursor-not-allowed"
                        )}
                    >
                        <span className={cn(!timeSlot && "text-muted-foreground")}>
                            {timeDisplay}
                        </span>
                        <ChevronDown className="size-3.5 text-muted-foreground" />
                    </button>
                </PopoverTrigger>
                <PopoverContent
                    className="w-44 p-1 max-h-64 overflow-y-auto"
                    align="end"
                >
                    {/* Only render time slot buttons when popover is open to avoid creating 96+ elements on every render */}
                    {timeOpen && (
                        <div className="flex flex-col">
                            {timeSlots.map((slot) => (
                                <button
                                    key={slot.value}
                                    type="button"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        onTimeSlotChange(slot.value);
                                        setTimeOpen(false);
                                    }}
                                    className={cn(
                                        optionButtonStyles,
                                        timeSlot === slot.value && "bg-accent"
                                    )}
                                >
                                    {slot.display}
                                </button>
                            ))}
                        </div>
                    )}
                </PopoverContent>
            </Popover>

            {/* Search Button */}
            {showSearchButton && (
                <div className="pr-1.5 pl-1">
                    <Button size="icon" className="rounded-full" onClick={onSearch}>
                        <Search className="size-4" />
                    </Button>
                </div>
            )}
        </div>
    );
}

export { UnifiedSearchControls };
