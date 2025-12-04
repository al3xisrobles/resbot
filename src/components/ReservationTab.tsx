import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { AlertCircle, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { makeReservation } from '@/lib/api'
import { cn } from '@/lib/utils'
import { TIME_SLOTS } from '@/lib/time-slots'
import { useVenue } from '@/contexts/VenueContext'

export function ReservationTab() {
  const { selectedVenueId } = useVenue()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const [reservationForm, setReservationForm] = useState({
    venueId: '',
    partySize: '2',
    date: undefined as Date | undefined,
    timeSlot: '19:0', // Default to 7:00 PM
    windowHours: '1',
    seatingType: 'any',
    dropTimeSlot: '9:0', // Default to 9:00 AM
  })

  // Auto-populate venue ID from search selection
  useEffect(() => {
    if (selectedVenueId) {
      setReservationForm(prev => ({ ...prev, venueId: selectedVenueId }))
    }
  }, [selectedVenueId])

  const handleMakeReservation = async () => {
    if (!reservationForm.date) {
      setError('Please select a reservation date')
      return
    }

    setLoading(true)
    setError(null)
    setSuccessMessage(null)

    try {
      // Parse time slot
      const [hour, minute] = reservationForm.timeSlot.split(':')
      const [dropHour, dropMinute] = reservationForm.dropTimeSlot.split(':')

      const result = await makeReservation({
        venueId: reservationForm.venueId,
        partySize: reservationForm.partySize,
        date: format(reservationForm.date, 'yyyy-MM-dd'),
        hour,
        minute,
        windowHours: reservationForm.windowHours,
        seatingType: reservationForm.seatingType === 'any' ? undefined : reservationForm.seatingType,
        dropHour,
        dropMinute,
      })
      setSuccessMessage(`Reservation successful! Token: ${result.resy_token}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to make reservation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className='px-10 py-16'>
      <CardHeader>
        <CardTitle>Make a Reservation</CardTitle>
        <CardDescription>
          Configure reservation details and timing
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Error/Success Messages */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {successMessage && (
          <Alert className="border-green-500 bg-green-50 text-green-900">
            <CheckCircle2 className="size-4 text-green-600" />
            <AlertDescription>{successMessage}</AlertDescription>
          </Alert>
        )}

        {/* Basic Info */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Restaurant ID</Label>
            <Input
              id="res-venue-id"
              placeholder="e.g., 32520"
              value={reservationForm.venueId}
              onChange={(e) => setReservationForm({ ...reservationForm, venueId: e.target.value })}
            />
          </div>
          <div>
            <Label className="flex items-center gap-2">
              Party Size
            </Label>
            <Select
              value={reservationForm.partySize}
              onValueChange={(value) => setReservationForm({ ...reservationForm, partySize: value })}
            >
              <SelectTrigger id="party-size">
                <SelectValue placeholder="Select party size" />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 6 }, (_, i) => i + 1).map((size) => (
                  <SelectItem key={size} value={size.toString()}>
                    {size} {size === 1 ? 'person' : 'people'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Date & Time */}
        <div className="space-y-4">
          <h3 className="flex items-center gap-2">
            Date & Time
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Reservation Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <button
                    className={cn(
                      "flex h-10 w-full items-center justify-start rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors",
                      !reservationForm.date && "text-muted-foreground"
                    )}
                  >
                    {reservationForm.date ? format(reservationForm.date, 'PPP') : <span>Pick a date</span>}
                  </button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={reservationForm.date}
                    onSelect={(date) => setReservationForm({ ...reservationForm, date })}
                  />
                </PopoverContent>
              </Popover>
            </div>
            <div>
              <Label>Desired Time</Label>
              <Select
                value={reservationForm.timeSlot}
                onValueChange={(value) => setReservationForm({ ...reservationForm, timeSlot: value })}
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
            </div>
          </div>
        </div>

        {/* Preferences */}
        <div className="space-y-4">
          <h3 className="text-lg flex items-center gap-2">
            Preferences
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Time Window (±hours)</Label>
              <Select
                value={reservationForm.windowHours}
                onValueChange={(value) => setReservationForm({ ...reservationForm, windowHours: value })}
              >
                <SelectTrigger id="window">
                  <SelectValue placeholder="Select window" />
                </SelectTrigger>
                <SelectContent>
                  {[0, 1, 2, 3, 4, 5, 6].map((hours) => (
                    <SelectItem key={hours} value={hours.toString()}>
                      ±{hours} {hours === 1 ? 'hour' : 'hours'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Seating Type (optional)</Label>
              <Select
                value={reservationForm.seatingType}
                onValueChange={(value) => setReservationForm({ ...reservationForm, seatingType: value })}
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
            </div>
          </div>
        </div>

        <Separator className='my-8'/>

        {/* Drop Time */}
        <div className="space-y-4">
          <h3 className="text-lg">Reservation Drop Time</h3>
          <p className="text-sm text-muted-foreground">
            When do reservations open? The bot will wait until this time.
          </p>
          <div>
            <Label>Drop Time</Label>
            <Select
              value={reservationForm.dropTimeSlot}
              onValueChange={(value) => setReservationForm({ ...reservationForm, dropTimeSlot: value })}
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
          </div>
        </div>

        {/* Submit */}
        <Button
          size="lg"
          onClick={handleMakeReservation}
          disabled={loading || !reservationForm.venueId || !reservationForm.date}
        >
          {loading ? 'Processing...' : 'Schedule'}
        </Button>
      </CardContent>
    </Card>
  )
}
