import { useNavigate } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Reservation } from "@/lib/mockReservations";

interface ReservationsDataTableProps {
  reservations: Reservation[];
}

export function ReservationsDataTable({
  reservations,
}: ReservationsDataTableProps) {
  const navigate = useNavigate();

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
            <TableHead className="w-[200px]">Restaurant</TableHead>
            <TableHead className="w-[150px]">Date</TableHead>
            <TableHead className="w-[100px]">Time</TableHead>
            <TableHead className="w-[100px] text-center">Party Size</TableHead>
            <TableHead className="w-[120px]">Status</TableHead>
            <TableHead>Notes</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {reservations.map((reservation) => (
            <TableRow key={reservation.id}>
              <TableCell>
                <p
                  className="font-medium w-max cursor-pointer hover:underline underline-offset-2"
                  onClick={() =>
                    window.open(`/venue?id=${reservation.venueId}`, "_blank")
                  }
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
                {reservation.note || "-"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
