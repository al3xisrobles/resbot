import { useState } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import type { Reservation } from "../lib/types";

interface ReservationsDataTableProps {
    reservations: Reservation[];
}

export function ReservationsDataTable({
    reservations,
}: ReservationsDataTableProps) {
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

    const toggleRow = (id: string) => {
        setExpandedRows((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const getStatusColor = (status: Reservation["status"]) => {
        switch (status) {
            case "Scheduled":
                return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
            case "Succeeded":
                return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
            case "Failed":
                return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
        }
    };

    const formatDate = (dateStr: string) => {
        // Parse date as local time by splitting the string to avoid timezone conversion
        // e.g., "2025-12-05" should display as Dec 5, not Dec 4
        const [year, month, day] = dateStr.split("-").map(Number);
        const date = new Date(year, month - 1, day);
        return date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
        });
    };

    const formatTime = (timeStr: string) => {
        const [hours, minutes] = timeStr.split(":");
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? "PM" : "AM";
        const displayHour = hour % 12 || 12;
        return `${displayHour}:${minutes} ${ampm}`;
    };

    const formatSnipeTime = (snipeTimeIso: string | undefined, status: Reservation["status"]) => {
        if (!snipeTimeIso) return "-";

        try {
            const snipeDate = new Date(snipeTimeIso);
            const formattedDate = snipeDate.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
            });
            const formattedTime = snipeDate.toLocaleTimeString("en-US", {
                hour: "numeric",
                minute: "2-digit",
            });

            if (status === "Scheduled") {
                return `Scheduled for ${formattedDate} ${formattedTime}`;
            } else {
                return `Ran at ${formattedDate} ${formattedTime}`;
            }
        } catch {
            return "-";
        }
    };

    if (reservations.length === 0) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                No reservations found
            </div>
        );
    }

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-[40px]"></TableHead>
                        <TableHead className="w-[200px]">Restaurant</TableHead>
                        <TableHead className="w-[150px]">Date</TableHead>
                        <TableHead className="w-[100px]">Time</TableHead>
                        <TableHead className="w-[100px] text-center">Party Size</TableHead>
                        <TableHead className="w-[120px]">Status</TableHead>
                        <TableHead className="w-[200px]">Snipe Time</TableHead>
                        <TableHead>Notes</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {reservations.map((reservation) => {
                        const isExpanded = expandedRows.has(reservation.id);
                        const notes = reservation.aiSummary || reservation.note || "-";
                        const hasNotes = notes !== "-";

                        return (
                            <>
                                <TableRow
                                    key={reservation.id}
                                    className={hasNotes ? "cursor-pointer hover:bg-muted/50" : ""}
                                    onClick={() => hasNotes && toggleRow(reservation.id)}
                                >
                                    <TableCell>
                                        {hasNotes && (
                                            <div className="h-6 w-6 flex items-center justify-center">
                                                {isExpanded ? (
                                                    <ChevronDown className="h-4 w-4" />
                                                ) : (
                                                    <ChevronRight className="h-4 w-4" />
                                                )}
                                            </div>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        <p
                                            className="font-medium w-max cursor-pointer hover:underline underline-offset-2"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                window.open(`/venue?id=${reservation.venueId}`, "_blank");
                                            }}
                                        >
                                            {reservation.venueName}
                                        </p>
                                    </TableCell>
                                    <TableCell>{formatDate(reservation.date)}</TableCell>
                                    <TableCell>{formatTime(reservation.time)}</TableCell>
                                    <TableCell className="text-center">
                                        {reservation.partySize}
                                    </TableCell>
                                    <TableCell>
                                        <span
                                            className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                                                reservation.status
                                            )}`}
                                        >
                                            {reservation.status}
                                        </span>
                                    </TableCell>
                                    <TableCell className="text-muted-foreground text-sm">
                                        {formatSnipeTime(reservation.snipeTime, reservation.status)}
                                    </TableCell>
                                    <TableCell className="text-muted-foreground text-sm">
                                        {hasNotes ? (
                                            <span className="truncate block max-w-[200px]">
                                                {notes}
                                            </span>
                                        ) : (
                                            "-"
                                        )}
                                    </TableCell>
                                </TableRow>
                                {isExpanded && hasNotes && (
                                    <TableRow key={`${reservation.id}-expanded`}>
                                        <TableCell colSpan={8} className="bg-muted/50">
                                            <div className="py-2 px-4">
                                                <p className="text-sm text-muted-foreground whitespace-pre-wrap wrap-break-word">
                                                    {notes}
                                                </p>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                )}
                            </>
                        );
                    })}
                </TableBody>
            </Table>
        </div>
    );
}
