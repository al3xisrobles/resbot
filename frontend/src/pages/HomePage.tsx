import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { Search, AlertCircle, MapPin, ChevronRight, Calendar as CalendarIcon } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { searchRestaurants, getVenuePhoto } from '@/lib/api'
import { useVenue } from '@/contexts/VenueContext'
import { TIME_SLOTS } from '@/lib/time-slots'
import { cn } from '@/lib/utils'

export function HomePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const {
    searchResults,
    setSearchResults,
    searchQuery,
    setSearchQuery,
    reservationForm,
    setReservationForm
  } = useVenue()

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a restaurant name')
      return
    }

    setLoading(true)
    setError(null)
    setSearchResults([])

    try {
      const results = await searchRestaurants(searchQuery)
      setSearchResults(results)

      if (results.length === 0) {
        setError('No restaurants found matching your search')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search restaurants')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectVenue = (venueId: string) => {
    navigate(`/venue?id=${venueId}`)
  }

  // Prefetch images for all search results
  useEffect(() => {
    if (searchResults.length === 0) return

    const prefetchImages = async () => {
      // Prefetch images for all results in the background
      searchResults.forEach(async (result) => {
        try {
          await getVenuePhoto(result.id, result.name)
        } catch (err) {
          // Silently fail - prefetching is optional
          console.debug('Failed to prefetch photo for', result.name, err)
        }
      })
    }

    prefetchImages()
  }, [searchResults])

  return (
    <div className="min-h-screen bg-background">
      {/* Main Content */}
      <main className="container mx-auto px-4 py-24">
        <div className="w-full max-w-xl mx-auto">
          <Card className='px-10 py-16'>
            <CardHeader>
              <CardTitle>Restaurant Search</CardTitle>
              <CardDescription>
                Search for restaurants by name to make a reservation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Error Messages */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="size-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-4">

                                {/* Reservation Details */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  {/* Party Size */}
                  <div>
                    <Label htmlFor="party-size">Party Size</Label>
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

                  {/* Date */}
                  <div>
                    <Label>Date</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <button
                          className={cn(
                            "flex h-10 w-full items-center justify-start rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors",
                            !reservationForm.date && "text-muted-foreground"
                          )}
                        >
                          {reservationForm.date ? format(reservationForm.date, 'EEE, MMM d') : <span>Pick a date</span>}
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

                  {/* Time */}
                  <div>
                    <Label htmlFor="time-slot">Desired Time</Label>
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

                {/* Search Bar */}
                <div className="flex gap-4">
                  <div className="flex-1">
                    <Label htmlFor="search-query">Restaurant Name</Label>
                    <Input
                      id="search-query"
                      placeholder="e.g., Carbone, Torrisi"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    />
                  </div>
                  <div className="flex items-end">
                    <Button onClick={handleSearch} disabled={loading || !searchQuery}>
                      <Search className="mr-2 size-4" />
                      {loading ? 'Searching...' : 'Search'}
                    </Button>
                  </div>
                </div>


              </div>

              {/* Search Results */}
              {searchResults.length > 0 && (
                <div className="space-y-2 pt-4">
                  <p className="text-sm text-muted-foreground">
                    Found {searchResults.length} {searchResults.length === 1 ? 'restaurant' : 'restaurants'}
                  </p>
                  <div className="space-y-2">
                    {searchResults.map((result) => (
                      <button
                        key={result.id}
                        onClick={() => handleSelectVenue(result.id)}
                        className="w-full text-left p-4 rounded-lg border hover:border-primary hover:bg-accent/50 transition-all group"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 space-y-1">
                            <div className="flex items-center gap-2">
                              <h4 className="font-semibold group-hover:text-primary transition-colors">
                                {result.name}
                              </h4>
                              {result.price_range > 0 && (
                                <span className="text-sm text-muted-foreground">
                                  {'$'.repeat(result.price_range)}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <MapPin className="size-3" />
                              <span>
                                {[result.neighborhood, result.locality, result.region]
                                  .filter(Boolean)
                                  .filter(item => item !== 'N/A')
                                  .join(', ')}
                              </span>
                            </div>
                            {result.type && result.type !== "N/A" && (
                              <p className="text-sm text-muted-foreground">{result.type}</p>
                            )}
                          </div>
                          <ChevronRight className="size-5 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
