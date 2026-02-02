import type { ComponentProps } from "react";
import { Calendar as CalendarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import type { VariantProps } from "class-variance-authority";
import { buttonVariants } from "./button";

export interface DatePickerTriggerProps
    extends Omit<ComponentProps<typeof Button>, "children">,
    VariantProps<typeof buttonVariants> {
    /** Display text when date is selected */
    displayText?: string;
    /** Placeholder text when no date is selected */
    placeholder?: string;
    /** Whether to show the calendar icon */
    showIcon?: boolean;
}

function DatePickerTrigger({
    className,
    variant = "outline",
    displayText,
    placeholder = "Pick a date",
    showIcon = true,
    ...props
}: DatePickerTriggerProps) {
    const hasValue = !!displayText;

    return (
        <Button
            variant={variant}
            className={cn(
                "w-full justify-start text-left font-normal",
                !hasValue && "text-muted-foreground",
                className
            )}
            {...props}
        >
            {showIcon && <CalendarIcon className="mr-2 size-4" />}
            {hasValue ? <span>{displayText}</span> : <span>{placeholder}</span>}
        </Button>
    );
}

export { DatePickerTrigger };
