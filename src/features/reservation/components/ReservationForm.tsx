import { format } from "date-fns";
import { LoaderCircle, CircleCheck, AlertCircle, Plus, X } from "lucide-react";
import { useAtom } from "jotai";
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
import { Separator } from "@/components/ui/separator";
import { DatePickerTrigger } from "@/components/ui/date-picker-trigger";
import { UnifiedSearchControls } from "@/components/ui/unified-search-controls";
import { TIME_SLOTS } from "@/lib/time-slots";
import { useAuth } from "@/contexts/AuthContext";
import { cityTimezoneAbbrAtom } from "@/atoms/cityAtom";
import type { ReservationFormState, DropSchedule } from "../atoms/reservationFormAtom";
import { Stack, Group } from "@/components/ui/layout";

const useEmulators =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

interface ReservationFormProps {
  reservationForm: ReservationFormState;
  setReservationForm: (form: ReservationFormState | ((prev: ReservationFormState) => ReservationFormState)) => void;
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
  const [timezoneAbbr] = useAtom(cityTimezoneAbbrAtom);

  return (
    <Stack itemsSpacing={24}>
      <Stack itemsSpacing={4}>
        <h2 className="text-2xl font-bold">Schedule a Reservation Snipe</h2>
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
      <Stack itemsSpacing={8} className="w-fit">
        <Label>Reservation Details</Label>
        <UnifiedSearchControls
          partySize={reservationForm.partySize}
          onPartySizeChange={(partySize) =>
            setReservationForm({ ...reservationForm, partySize })
          }
          date={reservationForm.date}
          onDateChange={(date) =>
            setReservationForm({ ...reservationForm, date })
          }
          timeSlot={reservationForm.timeSlot}
          onTimeSlotChange={(timeSlot) =>
            setReservationForm({ ...reservationForm, timeSlot })
          }
          timeSlots={TIME_SLOTS}
          showSearchButton={false}
          disabled={!auth.currentUser}
        />
      </Stack>

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
              <SelectTrigger variant="pill" id="window">
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
              <SelectTrigger variant="pill" id="seating-type">
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
            When do reservations open? The bot will wait until this time. You can schedule multiple snipes at different times.
          </p>
        </Stack>
        <Stack itemsSpacing={12}>
          {reservationForm.dropSchedules.map((schedule) => (
            <Group
              key={schedule.id}
              itemsSpacing={16}
              noWrap
              className="flex-col md:flex-row items-end"
            >
              <Stack itemsSpacing={8} className="flex-1">
                <Label>Drop Date</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <DatePickerTrigger
                      disabled={!auth.currentUser}
                      displayText={
                        schedule.dropDate
                          ? format(schedule.dropDate, "EEE, MMM d")
                          : undefined
                      }
                      placeholder="Pick drop date"
                    />
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={schedule.dropDate}
                      onSelect={(date) => {
                        setReservationForm((prev: ReservationFormState) => ({
                          ...prev,
                          dropSchedules: prev.dropSchedules.map((s: DropSchedule) =>
                            s.id === schedule.id ? { ...s, dropDate: date } : s
                          ),
                        }));
                      }}
                    />
                  </PopoverContent>
                </Popover>
              </Stack>
              <Stack itemsSpacing={8} className="flex-1">
                <Label className="flex flex-row gap-2 items-center">
                  <p>Drop Time ({timezoneAbbr})</p>
                </Label>
                <Select
                  value={schedule.dropTimeSlot}
                  onValueChange={(value) => {
                    setReservationForm((prev: ReservationFormState) => ({
                      ...prev,
                      dropSchedules: prev.dropSchedules.map((s: DropSchedule) =>
                        s.id === schedule.id ? { ...s, dropTimeSlot: value } : s
                      ),
                    }));
                  }}
                  disabled={!auth.currentUser}
                >
                  <SelectTrigger variant="pill" id={`drop-time-slot-${schedule.id}`}>
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
              {reservationForm.dropSchedules.length > 1 && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setReservationForm((prev: ReservationFormState) => ({
                      ...prev,
                      dropSchedules: prev.dropSchedules.filter((s: DropSchedule) => s.id !== schedule.id),
                    }));
                  }}
                  disabled={!auth.currentUser}
                  className="shrink-0 translate-y-[10px]"
                >
                  <X className="size-4" />
                </Button>
              )}
            </Group>
          ))}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setReservationForm((prev: ReservationFormState) => ({
                ...prev,
                dropSchedules: [
                  ...prev.dropSchedules,
                  {
                    id: crypto.randomUUID(),
                    dropDate: undefined,
                    dropTimeSlot: "9:0",
                  },
                ],
              }));
            }}
            disabled={!auth.currentUser}
            className="w-full gap-2"
          >
            <Plus className="size-4" />
          </Button>
        </Stack>
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
              // Set all drop dates/times to now
              const now = new Date();
              setReservationForm((prev: ReservationFormState) => ({
                ...prev,
                dropSchedules: prev.dropSchedules.map((schedule: DropSchedule) => ({
                  ...schedule,
                  dropDate: now,
                  dropTimeSlot: `${now.getHours()}:${now.getMinutes()}`,
                })),
              }));
            }}
          >
            Set all times to now
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
          reservationForm.dropSchedules.length === 0 ||
          reservationForm.dropSchedules.some(
            (schedule) => !schedule.dropDate
          )
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
