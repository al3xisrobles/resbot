import { format } from "date-fns";
import { Calendar as CalendarIcon, LoaderCircle, CircleCheck } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { TIME_SLOTS } from "@/lib/time-slots";
import { useAuth } from "@/contexts/AuthContext";
import type { ReservationFormState } from "../atoms/reservationFormAtom";
import { Stack, Group } from "@/components/ui/layout";

const useEmulators =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

interface ReservationFormProps {
  reservationForm: ReservationFormState;
  setReservationForm: (form: ReservationFormState) => void;
  onSchedule: () => void;
  loadingSubmit: boolean;
  error: string | null;
  reservationScheduled: boolean;
  reserveOnEmulation: boolean;
  setReserveOnEmulation: (value: boolean) => void;
}

export function ReservationForm({
  reservationForm,
  setReservationForm,
  onSchedule,
  loadingSubmit,
  error,
  reservationScheduled,
  reserveOnEmulation,
  setReserveOnEmulation,
}: ReservationFormProps) {
  const auth = useAuth();

  return (
    <Stack itemsSpacing={24}>
      <Stack itemsSpacing={4}>
        <h2 className="text-2xl font-bold">Make a Reservation</h2>
        <p className="text-sm text-muted-foreground">
          Configure reservation details and timing
        </p>
      </Stack>
      {/* Error Messages */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Reservation Details */}
      <Group itemsSpacing={16} noWrap className="flex-col md:flex-row">
        {/* Party Size */}
        <Stack itemsSpacing={8} className="flex-1">
          <Label htmlFor="party-size">Party Size</Label>
          <Select
            value={reservationForm.partySize}
            onValueChange={(value) =>
              setReservationForm({
                ...reservationForm,
                partySize: value,
              })
            }
            disabled={!auth.currentUser}
          >
            <SelectTrigger id="party-size">
              <SelectValue placeholder="Select party size" />
            </SelectTrigger>
            <SelectContent>
              {Array.from({ length: 6 }, (_, i) => i + 1).map((size) => (
                <SelectItem key={size} value={size.toString()}>
                  {size} {size === 1 ? "person" : "people"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Stack>

        {/* Date */}
        <Stack itemsSpacing={8} className="flex-1">
          <Label>Date</Label>
          <Popover>
            <PopoverTrigger asChild>
              <button
                disabled={!auth.currentUser}
                className={cn(
                  "flex h-9 w-full items-center justify-start rounded-md border bg-background px-3 py-2 text-sm shadow-xs ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors",
                  !reservationForm.date && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 size-4" />
                {reservationForm.date ? (
                  format(reservationForm.date, "EEE, MMM d")
                ) : (
                  <span>Pick a date</span>
                )}
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={reservationForm.date}
                onSelect={(date) =>
                  setReservationForm({ ...reservationForm, date })
                }
              />
            </PopoverContent>
          </Popover>
        </Stack>

        {/* Time */}
        <Stack itemsSpacing={8} className="flex-1">
          <Label htmlFor="time-slot">Desired Time (EST)</Label>
          <Select
            value={reservationForm.timeSlot}
            onValueChange={(value) =>
              setReservationForm({
                ...reservationForm,
                timeSlot: value,
              })
            }
            disabled={!auth.currentUser}
          >
            <SelectTrigger id="time-slot">
              <SelectValue placeholder="Select time" />
            </SelectTrigger>
            <SelectContent>
              {TIME_SLOTS.map((slot) => (
                <SelectItem key={slot.value} value={slot.value}>
                  {slot.display}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Stack>
      </Group>

      {/* Preferences */}
      <Stack itemsSpacing={16}>
        <h3 className="text-lg flex items-center gap-2">Preferences</h3>
        <Group itemsSpacing={16} noWrap className="flex-col md:flex-row">
          <Stack itemsSpacing={8} className="flex-1">
            <Label>Time Window (±hours)</Label>
            <Select
              value={reservationForm.windowHours}
              onValueChange={(value) =>
                setReservationForm({
                  ...reservationForm,
                  windowHours: value,
                })
              }
              disabled={!auth.currentUser}
            >
              <SelectTrigger id="window">
                <SelectValue placeholder="Select window" />
              </SelectTrigger>
              <SelectContent>
                {[0, 1, 2, 3, 4, 5, 6].map((hours) => (
                  <SelectItem key={hours} value={hours.toString()}>
                    ±{hours} {hours === 1 ? "hour" : "hours"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Stack>
          <Stack itemsSpacing={8} className="flex-1">
            <Label>Seating Type Preference (optional)</Label>
            <Select
              value={reservationForm.seatingType}
              onValueChange={(value) =>
                setReservationForm({
                  ...reservationForm,
                  seatingType: value,
                })
              }
              disabled={!auth.currentUser}
            >
              <SelectTrigger id="seating-type">
                <SelectValue placeholder="Any seating" />
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
          </Stack>
        </Group>
      </Stack>

      <Separator />

      {/* Drop Time */}
      <Stack itemsSpacing={16}>
        <Stack itemsSpacing={4}>
          <h3 className="text-lg">Reservation Drop Time</h3>
          <p className="text-sm text-muted-foreground">
            When do reservations open? The bot will wait until this time.
          </p>
        </Stack>
        <Group itemsSpacing={16} noWrap className="flex-col md:flex-row">
          <Stack itemsSpacing={8} className="flex-1">
            <Label>Drop Date</Label>
            <Popover>
              <PopoverTrigger asChild>
                <button
                  disabled={!auth.currentUser}
                  className={cn(
                    "flex h-9 w-full items-center justify-start rounded-md border bg-background px-3 py-2 text-sm shadow-xs ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors",
                    !reservationForm.dropDate && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 size-4" />
                  {reservationForm.dropDate ? (
                    format(reservationForm.dropDate, "EEE, MMM d")
                  ) : (
                    <span>Pick drop date</span>
                  )}
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={reservationForm.dropDate}
                  onSelect={(date) =>
                    setReservationForm({
                      ...reservationForm,
                      dropDate: date,
                    })
                  }
                />
              </PopoverContent>
            </Popover>
          </Stack>
          <Stack itemsSpacing={8} className="flex-1">
            <Label className="flex flex-row gap-2 items-center">
              <p>Drop Time (EST)</p>
            </Label>
            <Select
              value={reservationForm.dropTimeSlot}
              onValueChange={(value) =>
                setReservationForm({
                  ...reservationForm,
                  dropTimeSlot: value,
                })
              }
              disabled={!auth.currentUser}
            >
              <SelectTrigger id="drop-time-slot">
                <SelectValue placeholder="Select drop time" />
              </SelectTrigger>
              <SelectContent>
                {TIME_SLOTS.map((slot) => (
                  <SelectItem key={slot.value} value={slot.value}>
                    {slot.display}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Stack>
        </Group>
      </Stack>

      {useEmulators && (
        <Group itemsSpacing={8}>
          <Button
            size="sm"
            variant={reserveOnEmulation ? "default" : "outline"}
            onClick={() => setReserveOnEmulation(!reserveOnEmulation)}
          >
            Actually Reserve Now
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              // Set drop date/time to now
              const now = new Date();
              setReservationForm({
                ...reservationForm,
                dropDate: now,
                dropTimeSlot: `${now.getHours()}:${now.getMinutes()}`,
              });
            }}
          >
            Set time to now
          </Button>
        </Group>
      )}

      {/* Submit */}
      <Button
        size="lg"
        onClick={onSchedule}
        disabled={
          !auth.currentUser ||
          loadingSubmit ||
          reservationScheduled ||
          !reservationForm.date ||
          !reservationForm.dropDate
        }
        className="w-full"
      >
        {loadingSubmit && (
          <LoaderCircle className="mr-2 size-4 animate-spin" />
        )}
        {reservationScheduled && <CircleCheck className="mr-2 size-4" />}
        {reservationScheduled
          ? "Reservation Scheduled"
          : loadingSubmit
            ? "Scheduling..."
            : "Schedule Reservation"}
      </Button>
    </Stack>
  );
}
