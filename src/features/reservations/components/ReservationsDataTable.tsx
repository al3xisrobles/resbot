import * as Sentry from "@sentry/react";
import { useState } from "react";
import { ChevronRight, ChevronDown, MoreHorizontal, Edit, X } from "lucide-react";
import { format } from "date-fns";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Reservation } from "../lib/types";
import { updateReservationJob, cancelReservationJob } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

interface ReservationsDataTableProps {
    reservations: Reservation[];
    onRefetch?: () => Promise<void>;
}

interface EditFormData {
    date: Date | undefined;
    hour: number;
    minute: number;
    partySize: number;
    windowHours: number;
    seatingType: string;
    dropDate: Date | undefined;
    dropHour: number;
    dropMinute: number;
}

export function ReservationsDataTable({
    reservations,
    onRefetch,
}: ReservationsDataTableProps) {
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
    const [editingJobId, setEditingJobId] = useState<string | null>(null);
    const [cancellingJobId, setCancellingJobId] = useState<string | null>(null);
    const [showCancelDialog, setShowCancelDialog] = useState(false);
    const [editFormData, setEditFormData] = useState<EditFormData | null>(null);
    const [editLoading, setEditLoading] = useState(false);
    const [editError, setEditError] = useState<string | null>(null);
    const [cancelLoading, setCancelLoading] = useState(false);
    const [cancelError, setCancelError] = useState<string | null>(null);
    const auth = useAuth();

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

    const handleEditClick = (reservation: Reservation) => {
        // Parse date strings to Date objects
        const [year, month, day] = reservation.date.split("-").map(Number);
        const date = new Date(year, month - 1, day);

        const [hours, minutes] = reservation.time.split(":").map(Number);

        // Parse drop date - use dropDate if available, otherwise parse from snipeTime
        let dropDate: Date;
        let dropHour: number;
        let dropMinute: number;

        if (reservation.dropDate) {
            const [dropYear, dropMonth, dropDay] = reservation.dropDate.split("-").map(Number);
            dropDate = new Date(dropYear, dropMonth - 1, dropDay);
            dropHour = reservation.dropHour ?? 9;
            dropMinute = reservation.dropMinute ?? 0;
        } else if (reservation.snipeTime) {
            dropDate = new Date(reservation.snipeTime);
            dropHour = dropDate.getHours();
            dropMinute = dropDate.getMinutes();
        } else {
            dropDate = new Date(date);
            dropHour = 9;
            dropMinute = 0;
        }

        setEditFormData({
            date,
            hour: hours,
            minute: minutes,
            partySize: reservation.partySize,
            windowHours: reservation.windowHours ?? 1,
            seatingType: reservation.seatingType ?? "any",
            dropDate,
            dropHour,
            dropMinute,
        });
        setEditingJobId(reservation.id);
        setExpandedRows((prev) => new Set(prev).add(reservation.id));
        setEditError(null);
    };

    const handleCancelEdit = () => {
        setEditingJobId(null);
        setEditFormData(null);
        setEditError(null);
    };

    const handleSaveEdit = async () => {
        if (!editingJobId || !editFormData || !auth.currentUser) return;

        if (!editFormData.date || !editFormData.dropDate) {
            setEditError("Please select both reservation date and drop date");
            return;
        }

        setEditLoading(true);
        setEditError(null);

        try {
            await updateReservationJob(auth.currentUser.uid, editingJobId, {
                date: format(editFormData.date, "yyyy-MM-dd"),
                hour: editFormData.hour,
                minute: editFormData.minute,
                partySize: editFormData.partySize,
                windowHours: editFormData.windowHours,
                seatingType: editFormData.seatingType === "any" ? undefined : editFormData.seatingType,
                dropDate: format(editFormData.dropDate, "yyyy-MM-dd"),
                dropHour: editFormData.dropHour,
                dropMinute: editFormData.dropMinute,
            });

            // Refresh data
            if (onRefetch) {
                await onRefetch();
            }

            // Close edit mode
            setEditingJobId(null);
            setEditFormData(null);
            setExpandedRows((prev) => {
                const next = new Set(prev);
                next.delete(editingJobId);
                return next;
            });
        } catch (error) {
            Sentry.captureException(error);
            setEditError(error instanceof Error ? error.message : "Failed to update reservation");
        } finally {
            setEditLoading(false);
        }
    };

    const handleCancelClick = (reservation: Reservation) => {
        setCancellingJobId(reservation.id);
        setShowCancelDialog(true);
        setCancelError(null);
    };

    const handleConfirmCancel = async () => {
        if (!cancellingJobId || !auth.currentUser) return;


        setCancelLoading(true);
        setCancelError(null);

        try {
            await cancelReservationJob(auth.currentUser.uid, cancellingJobId);

            // Refresh data
            if (onRefetch) {
                await onRefetch();
            }

            // Close dialog
            setShowCancelDialog(false);
            setCancellingJobId(null);
        } catch (error) {
            Sentry.captureException(error);
            setCancelError(error instanceof Error ? error.message : "Failed to cancel reservation");
        } finally {
            setCancelLoading(false);
        }
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

    // Generate time options for select
    const generateTimeOptions = () => {
        const options = [];
        for (let hour = 0; hour < 24; hour++) {
            for (let minute = 0; minute < 60; minute += 15) {
                const displayHour = hour % 12 || 12;
                const ampm = hour >= 12 ? "PM" : "AM";
                const value = `${hour}:${minute.toString().padStart(2, "0")}`;
                const label = `${displayHour}:${minute.toString().padStart(2, "0")} ${ampm}`;
                options.push({ value, label });
            }
        }
        return options;
    };

    const timeOptions = generateTimeOptions();

    if (reservations.length === 0) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                No reservations found
            </div>
        );
    }

    return (
        <>
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
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {reservations.map((reservation) => {
                            const isExpanded = expandedRows.has(reservation.id);
                            const isEditing = editingJobId === reservation.id;
                            const notes = reservation.aiSummary || reservation.note || "-";
                            const hasNotes = notes !== "-";
                            const isScheduled = reservation.status === "Scheduled";

                            return (
                                <>
                                    <TableRow
                                        key={reservation.id}
                                        className={hasNotes && !isScheduled ? "cursor-pointer" : ""}
                                        onClick={() => hasNotes && !isScheduled && !isEditing && toggleRow(reservation.id)}
                                    >
                                        <TableCell>
                                            {hasNotes && !isScheduled && (
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
                                        <TableCell>
                                            {isScheduled ? (
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-8 w-8"
                                                            onClick={(e) => e.stopPropagation()}
                                                        >
                                                            <MoreHorizontal className="h-4 w-4" />
                                                        </Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleEditClick(reservation);
                                                            }}
                                                        >
                                                            <Edit className="mr-2 h-4 w-4" />
                                                            Edit
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem
                                                            variant="destructive"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleCancelClick(reservation);
                                                            }}
                                                        >
                                                            <X className="mr-2 h-4 w-4" />
                                                            Cancel
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            ) : hasNotes ? (
                                                <span className="text-muted-foreground text-sm truncate block max-w-[200px]">
                                                    {notes}
                                                </span>
                                            ) : (
                                                "-"
                                            )}
                                        </TableCell>
                                    </TableRow>
                                    {isExpanded && isEditing && editFormData && (
                                        <TableRow key={`${reservation.id}-edit`} className="hover:bg-transparent">
                                            <TableCell colSpan={8} className="p-4">
                                                <div className="space-y-4">
                                                    <div className="text-sm font-medium">Edit Reservation</div>
                                                    <div className="grid grid-cols-2 gap-4">
                                                        {/* Reservation Date */}
                                                        <div className="space-y-2">
                                                            <Label>Reservation Date</Label>
                                                            <Popover>
                                                                <PopoverTrigger asChild>
                                                                    <Button
                                                                        variant="outline"
                                                                        className={cn(
                                                                            "w-full justify-start text-left font-normal",
                                                                            !editFormData.date && "text-muted-foreground"
                                                                        )}
                                                                    >
                                                                        <CalendarIcon className="mr-2 h-4 w-4" />
                                                                        {editFormData.date ? (
                                                                            format(editFormData.date, "PPP")
                                                                        ) : (
                                                                            <span>Pick a date</span>
                                                                        )}
                                                                    </Button>
                                                                </PopoverTrigger>
                                                                <PopoverContent className="w-auto p-0">
                                                                    <Calendar
                                                                        mode="single"
                                                                        selected={editFormData.date}
                                                                        onSelect={(date) =>
                                                                            setEditFormData({ ...editFormData, date })
                                                                        }
                                                                        initialFocus
                                                                    />
                                                                </PopoverContent>
                                                            </Popover>
                                                        </div>

                                                        {/* Reservation Time */}
                                                        <div className="space-y-2">
                                                            <Label>Reservation Time</Label>
                                                            <Select
                                                                value={`${editFormData.hour}:${editFormData.minute.toString().padStart(2, "0")}`}
                                                                onValueChange={(value) => {
                                                                    const [h, m] = value.split(":").map(Number);
                                                                    setEditFormData({ ...editFormData, hour: h, minute: m });
                                                                }}
                                                            >
                                                                <SelectTrigger>
                                                                    <SelectValue />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    {timeOptions.map((option) => (
                                                                        <SelectItem key={option.value} value={option.value}>
                                                                            {option.label}
                                                                        </SelectItem>
                                                                    ))}
                                                                </SelectContent>
                                                            </Select>
                                                        </div>

                                                        {/* Party Size */}
                                                        <div className="space-y-2">
                                                            <Label>Party Size</Label>
                                                            <Input
                                                                type="number"
                                                                min="1"
                                                                value={editFormData.partySize}
                                                                onChange={(e) =>
                                                                    setEditFormData({ ...editFormData, partySize: parseInt(e.target.value) || 1 })
                                                                }
                                                            />
                                                        </div>

                                                        {/* Window Hours */}
                                                        <div className="space-y-2">
                                                            <Label>Window Hours</Label>
                                                            <Input
                                                                type="number"
                                                                min="1"
                                                                value={editFormData.windowHours}
                                                                onChange={(e) =>
                                                                    setEditFormData({ ...editFormData, windowHours: parseInt(e.target.value) || 1 })
                                                                }
                                                            />
                                                        </div>

                                                        {/* Drop Date */}
                                                        <div className="space-y-2">
                                                            <Label>Drop Date</Label>
                                                            <Popover>
                                                                <PopoverTrigger asChild>
                                                                    <Button
                                                                        variant="outline"
                                                                        className={cn(
                                                                            "w-full justify-start text-left font-normal",
                                                                            !editFormData.dropDate && "text-muted-foreground"
                                                                        )}
                                                                    >
                                                                        <CalendarIcon className="mr-2 h-4 w-4" />
                                                                        {editFormData.dropDate ? (
                                                                            format(editFormData.dropDate, "PPP")
                                                                        ) : (
                                                                            <span>Pick a date</span>
                                                                        )}
                                                                    </Button>
                                                                </PopoverTrigger>
                                                                <PopoverContent className="w-auto p-0">
                                                                    <Calendar
                                                                        mode="single"
                                                                        selected={editFormData.dropDate}
                                                                        onSelect={(date) =>
                                                                            setEditFormData({ ...editFormData, dropDate: date })
                                                                        }
                                                                        initialFocus
                                                                    />
                                                                </PopoverContent>
                                                            </Popover>
                                                        </div>

                                                        {/* Drop Time */}
                                                        <div className="space-y-2">
                                                            <Label>Drop Time</Label>
                                                            <Select
                                                                value={`${editFormData.dropHour}:${editFormData.dropMinute.toString().padStart(2, "0")}`}
                                                                onValueChange={(value) => {
                                                                    const [h, m] = value.split(":").map(Number);
                                                                    setEditFormData({ ...editFormData, dropHour: h, dropMinute: m });
                                                                }}
                                                            >
                                                                <SelectTrigger>
                                                                    <SelectValue />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    {timeOptions.map((option) => (
                                                                        <SelectItem key={option.value} value={option.value}>
                                                                            {option.label}
                                                                        </SelectItem>
                                                                    ))}
                                                                </SelectContent>
                                                            </Select>
                                                        </div>

                                                        {/* Seating Type */}
                                                        <div className="space-y-2">
                                                            <Label>Seating Type</Label>
                                                            <Select
                                                                value={editFormData.seatingType}
                                                                onValueChange={(value) =>
                                                                    setEditFormData({ ...editFormData, seatingType: value })
                                                                }
                                                            >
                                                                <SelectTrigger>
                                                                    <SelectValue />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    <SelectItem value="any">Any seating</SelectItem>
                                                                    <SelectItem value="Indoor Dining">Indoor Dining</SelectItem>
                                                                    <SelectItem value="Outdoor Dining">Outdoor Dining</SelectItem>
                                                                    <SelectItem value="Bar Seating">Bar Seating</SelectItem>
                                                                    <SelectItem value="Counter Seating">Counter Seating</SelectItem>
                                                                    <SelectItem value="Patio">Patio</SelectItem>
                                                                </SelectContent>
                                                            </Select>
                                                        </div>
                                                    </div>

                                                    {editError && (
                                                        <div className="text-sm text-destructive">{editError}</div>
                                                    )}

                                                    <div className="flex justify-end gap-2">
                                                        <Button
                                                            variant="outline"
                                                            onClick={handleCancelEdit}
                                                            disabled={editLoading}
                                                        >
                                                            Cancel
                                                        </Button>
                                                        <Button
                                                            onClick={handleSaveEdit}
                                                            disabled={editLoading}
                                                        >
                                                            {editLoading ? "Saving..." : "Save"}
                                                        </Button>
                                                    </div>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    )}
                                    {isExpanded && hasNotes && !isScheduled && !isEditing && (
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

            {/* Cancel Confirmation Dialog */}
            <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Cancel Reservation</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to cancel this reservation attempt? This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    {cancelError && (
                        <div className="text-sm text-destructive">{cancelError}</div>
                    )}
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setShowCancelDialog(false);
                                setCancellingJobId(null);
                                setCancelError(null);
                            }}
                            disabled={cancelLoading}
                        >
                            No, Keep It
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleConfirmCancel}
                            disabled={cancelLoading}
                        >
                            {cancelLoading ? "Cancelling..." : "Yes, Cancel"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}