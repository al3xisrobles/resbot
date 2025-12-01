import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { ArrowLeft, LoaderCircle, AlertCircle, CheckCircle2, MapPin, Banknote, Sparkles, ExternalLink, RefreshCw, Map, CalendarRange, Calendar as CalendarIcon, ChevronDown, Bookmark, Share } from 'lucide-react'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from '@/components/ui/carousel'
import { makeReservation, searchRestaurant, getGeminiSearch, getCalendar, getVenuePhoto, getVenueLinks, type VenueData, type GeminiSearchResponse, type CalendarData, type VenuePhotoData, type VenueLinks, type VenueLinksResponse } from '@/lib/api'
import { cn } from '@/lib/utils'
import { TIME_SLOTS } from '@/lib/time-slots'
import { useVenue } from '@/contexts/VenueContext'
import { getVenueCache, saveAiInsights, saveVenueCache } from '@/services/firebase'

export function VenueDetailPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const venueId = searchParams.get('id')

  // Use context for reservation form to persist across navigation
  const { reservationForm, setReservationForm, aiSummaryCache, setAiSummaryCache } = useVenue()

  const [venueData, setVenueData] = useState<VenueData | null>(null)
  const [loadingVenue, setLoadingVenue] = useState(true)
  const [venueError, setVenueError] = useState<string | null>(null)

  const [aiSummary, setAiSummary] = useState<GeminiSearchResponse | null>(null)
  const [loadingAi, setLoadingAi] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [showAiDetails, setShowAiDetails] = useState(false)
  const [aiLastUpdated, setAiLastUpdated] = useState<number | null>(null)

  const [calendarData, setCalendarData] = useState<CalendarData | null>(null)
  const [loadingCalendar, setLoadingCalendar] = useState(false)
  const [calendarError, setCalendarError] = useState<string | null>(null)

  const [venuePhoto, setVenuePhoto] = useState<VenuePhotoData | null>(null)
  const [loadingPhoto, setLoadingPhoto] = useState(false)

  const [venueLinks, setVenueLinks] = useState<VenueLinks | null>(null)
  const [loadingLinks, setLoadingLinks] = useState(false)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const [isBookmarked, setIsBookmarked] = useState(false)

  // Fetch venue data
  useEffect(() => {
    if (!venueId) {
      setVenueError('No venue ID provided')
      setLoadingVenue(false)
      return
    }

    const fetchVenueData = async () => {
      try {
        setLoadingVenue(true)
        const data = await searchRestaurant(venueId)
        setVenueData(data)
      } catch (err) {
        setVenueError(err instanceof Error ? err.message : 'Failed to load venue')
      } finally {
        setLoadingVenue(false)
      }
    }

    fetchVenueData()
  }, [venueId])

  // Fetch AI summary when venue data is loaded
  useEffect(() => {
    if (!venueData?.name || !venueId) return

    // Check in-memory cache first
    if (aiSummaryCache[venueId]) {
      setAiSummary(aiSummaryCache[venueId])
      return
    }

    // If not in memory cache, check Firebase and fetch from API if needed
    const fetchAiSummary = async () => {
      try {
        setLoadingAi(true)
        setAiError(null)

        // Check Firebase cache
        const cachedData = await getVenueCache(venueId)

        if (cachedData?.aiInsights) {
          // Parse the cached AI insights back to GeminiSearchResponse
          const cachedSummary = JSON.parse(cachedData.aiInsights) as GeminiSearchResponse
          setAiSummary(cachedSummary)
          setAiLastUpdated(cachedData.lastUpdated)

          // Store in memory cache too
          setAiSummaryCache({
            ...aiSummaryCache,
            [venueId]: cachedSummary
          })
        } else {
          // Not in Firebase, fetch from API
          const summary = await getGeminiSearch(venueData.name, venueId)
          setAiSummary(summary)
          const now = Date.now()
          setAiLastUpdated(now)

          // Store in both caches
          setAiSummaryCache({
            ...aiSummaryCache,
            [venueId]: summary
          })

          // Save to Firebase
          await saveAiInsights(venueId, JSON.stringify(summary))
        }
      } catch (err) {
        setAiError(err instanceof Error ? err.message : 'Failed to load AI summary')
      } finally {
        setLoadingAi(false)
      }
    }

    fetchAiSummary()
  }, [venueData?.name, venueId, aiSummaryCache, setAiSummaryCache])

  // Fetch calendar data when venue is loaded
  useEffect(() => {
    if (!venueId) return

    const fetchCalendarData = async () => {
      try {
        setLoadingCalendar(true)
        setCalendarError(null)
        const data = await getCalendar(venueId, reservationForm.partySize)
        setCalendarData(data)
      } catch (err) {
        setCalendarError(err instanceof Error ? err.message : 'Failed to load calendar')
      } finally {
        setLoadingCalendar(false)
      }
    }

    fetchCalendarData()
  }, [venueId, reservationForm.partySize])

  // Fetch venue photo when venue data is loaded
  useEffect(() => {
    if (!venueData?.name || !venueId) return

    const fetchVenuePhoto = async () => {
      try {
        setLoadingPhoto(true)
        const photoData = await getVenuePhoto(venueId, venueData.name)
        setVenuePhoto(photoData)
      } catch (err) {
        // Silently fail - photo is optional
        console.error('Failed to load venue photo:', err)
      } finally {
        setLoadingPhoto(false)
      }
    }

    fetchVenuePhoto()
  }, [venueData?.name, venueId])

  // Fetch venue links (Google Maps, Resy) and venue data
  useEffect(() => {
    if (!venueId) return

    const fetchVenueLinksAndData = async () => {
      console.log('[VenueDetailPage] Starting venue links and data fetch...')
      try {
        setLoadingLinks(true)

        // Check Firebase cache first
        const cachedData = await getVenueCache(venueId)

        // Check if we have both links AND complete venue data in cache
        const hasCompleteCache = cachedData?.googleMapsLink !== undefined &&
                                 cachedData?.resyLink !== undefined &&
                                 cachedData?.venueName &&
                                 cachedData?.venueType // Ensure we have the new venue data fields

        if (hasCompleteCache) {
          // We have cached links and venue data, use them
          console.log('[VenueDetailPage] ✓ Using cached venue links and data from Firebase')
          setVenueLinks({
            googleMaps: cachedData.googleMapsLink || null,
            resy: cachedData.resyLink || null
          })

          // Use cached venue data
          if (cachedData.venueName && !venueData) {
            console.log('[VenueDetailPage] ✓ Using cached venue data from Firebase')
            setVenueData({
              name: cachedData.venueName,
              venue_id: venueId,
              type: cachedData.venueType || '',
              address: cachedData.address || '',
              neighborhood: cachedData.neighborhood || '',
              price_range: cachedData.priceRange || 0,
              rating: cachedData.rating || null
            })
            setLoadingVenue(false)
          }
        } else {
          // No cache, fetch from API
          console.log('[VenueDetailPage] Cache miss - fetching from API')
          const response: VenueLinksResponse = await getVenueLinks(venueId)
          setVenueLinks(response.links)

          const foundCount = Object.values(response.links).filter(link => link !== null).length
          console.log(`[VenueDetailPage] ✓ Venue links loaded successfully. ${foundCount}/2 links available`)

          // Save links and venue data to Firebase cache
          await saveVenueCache(venueId, {
            googleMapsLink: response.links.googleMaps || undefined,
            resyLink: response.links.resy || undefined,
            venueName: response.venueData.name,
            venueType: response.venueData.type,
            address: response.venueData.address,
            neighborhood: response.venueData.neighborhood,
            priceRange: response.venueData.priceRange,
            rating: response.venueData.rating
          })
          console.log('[VenueDetailPage] ✓ Saved venue links and data to Firebase cache')

          // Also update venue data if we haven't loaded it yet
          if (!venueData) {
            setVenueData({
              name: response.venueData.name,
              venue_id: venueId,
              type: response.venueData.type,
              address: response.venueData.address,
              neighborhood: response.venueData.neighborhood,
              price_range: response.venueData.priceRange,
              rating: response.venueData.rating
            })
            setLoadingVenue(false)
          }
        }
      } catch (err) {
        console.error('[VenueDetailPage] ✗ Failed to load venue links:', err)
      } finally {
        setLoadingLinks(false)
        console.log('[VenueDetailPage] Venue links fetch completed')
      }
    }

    fetchVenueLinksAndData()
  }, [venueId, venueData])

  // Manual refresh function
  const handleRefreshAiSummary = async () => {
    if (!venueData?.name || !venueId) return

    try {
      setLoadingAi(true)
      setAiError(null)
      const summary = await getGeminiSearch(venueData.name, venueId)
      setAiSummary(summary)
      const now = Date.now()
      setAiLastUpdated(now)

      // Update both caches
      setAiSummaryCache({
        ...aiSummaryCache,
        [venueId]: summary
      })

      // Update Firebase cache
      await saveAiInsights(venueId, JSON.stringify(summary))
    } catch (err) {
      setAiError(err instanceof Error ? err.message : 'Failed to load AI summary')
    } finally {
      setLoadingAi(false)
    }
  }

  const handleMakeReservation = async () => {
    if (!venueId) {
      setError('No venue ID available')
      return
    }

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
        venueId,
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

  if (!venueId) {
    return (
      <div className="container mx-auto px-4 py-24">
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>No venue ID provided</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background pt-32">
      {/* Header with Back Button */}
      <div className="bg-card">
        <div className="container mx-auto px-4 py-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="gap-2"
          >
            <ArrowLeft className="size-4" />
            Back to Search
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 pb-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Side - Restaurant Information */}
          <div>
            <div className="flex flex-col md:flex-row gap-4">
              {/* Restaurant Info Card */}
              <Card className="flex-1 relative pb-20">
                <CardContent className="space-y-4">
                  {loadingVenue && (
                    <div className="text-center py-8 text-muted-foreground">
                      Loading restaurant details...
                    </div>
                  )}

                  {venueError && (
                    <Alert variant="destructive">
                      <AlertCircle className="size-4" />
                      <AlertDescription>{venueError}</AlertDescription>
                    </Alert>
                  )}

                  {venueData && (
                    <div className="space-y-4">
                      <div>
                        <h2 className="text-4xl font-bold">{venueData.name}</h2>
                        <p className="text-muted-foreground">{venueData.type}</p>
                      </div>

                      <Separator />

                      <div className="space-y-3">
                        <div className="flex items-start gap-3">
                          <MapPin className="size-5 text-muted-foreground mt-0.5 shrink-0" />
                          <div>
                            <p className="font-medium">Address</p>
                            {venueLinks?.googleMaps ? (
                              <a
                                href={venueLinks.googleMaps}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-primary hover:underline cursor-pointer"
                              >
                                {venueData.address}
                              </a>
                            ) : (
                              <p className="text-sm text-muted-foreground">{venueData.address}</p>
                            )}
                            {venueData.neighborhood && (
                              <p className="text-sm text-muted-foreground">{venueData.neighborhood}</p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <Banknote className="size-5 text-muted-foreground shrink-0" />
                          <div>
                            <p className="font-medium">Price Range</p>
                            <p className="text-sm text-muted-foreground">
                              {'$'.repeat(venueData.price_range || 1)}
                            </p>
                          </div>
                        </div>
{/*
                        {venueData.rating && venueData.rating != 0 && venueData.rating != "0" && (
                          <div className="flex items-center gap-3">
                            <span className="text-lg">⭐</span>
                            <div>
                              <p className="font-medium">Rating</p>
                              <p className="text-sm text-muted-foreground">{venueData.rating}/5</p>
                            </div>
                          </div>
                        )} */}
                      </div>
                    </div>
                  )}

                  <div className="absolute bottom-0 left-0 right-0 p-6 space-y-3">
                    {/* Bookmark and Share Buttons */}
                    {venueData && (
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className={`gap-2 ${isBookmarked ? 'bg-primary/10' : ''}`}
                          onClick={() => setIsBookmarked(!isBookmarked)}
                        >
                          <Bookmark className={`size-4 ${isBookmarked ? 'fill-primary stroke-primary' : ''}`} />
                          {isBookmarked ? 'Bookmarked' : 'Bookmark'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-2"
                          onClick={() => {
                            const url = window.location.href
                            navigator.clipboard.writeText(url)
                            toast('Link copied to clipboard', {
                              description: 'Share this restaurant with friends'
                            })
                          }}
                        >
                          <Share className="size-4" />
                          Share
                        </Button>
                      </div>
                    )}

                    {/* Social Links */}
                    {venueData && (
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className={`flex-1 w-max gap-2 ${loadingLinks ? 'animate-pulse' : ''}`}
                            disabled={!venueLinks?.googleMaps || loadingLinks}
                            onClick={() => {
                              if (venueLinks?.googleMaps) {
                                console.log('[VenueDetailPage] Opening Google Maps link:', venueLinks.googleMaps)
                                window.open(venueLinks.googleMaps, '_blank')
                              }
                            }}
                          >
                            <Map className="size-4" />
                            Google Maps
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className={`flex-1 w-max gap-2 ${loadingLinks ? 'animate-pulse' : ''}`}
                            disabled={!venueLinks?.resy || loadingLinks}
                            onClick={() => {
                              if (venueLinks?.resy) {
                                console.log('[VenueDetailPage] Opening Resy link:', venueLinks.resy)
                                window.open(venueLinks.resy, '_blank')
                              }
                            }}
                          >
                            <CalendarRange className="size-4" />
                            Resy
                          </Button>
                        </div>
                    )}
                  </div>

                  {/* Social Links - Positioned at bottom */}
                </CardContent>
              </Card>

              {/* Availability Calendar */}
              <div className="shrink-0">
                {loadingCalendar && (
                  <div className="text-center py-8 text-muted-foreground">
                    Loading availability...
                  </div>
                )}

                {calendarError && (
                  <Alert variant="destructive">
                    <AlertCircle className="size-4" />
                    <AlertDescription>{calendarError}</AlertDescription>
                  </Alert>
                )}

                {calendarData && !loadingCalendar && (
                  <Calendar
                    mode="single"
                    selected={reservationForm.date}
                    onSelect={(date) => setReservationForm({ ...reservationForm, date })}
                    disabled={(date) => {
                      const dateStr = format(date, 'yyyy-MM-dd')
                      const dateEntry = calendarData.availability.find(a => a.date === dateStr)
                      const dateAvailable = dateEntry ? !dateEntry.closed : false
                      return !dateAvailable
                    }}
                    modifiers={{
                      available: (date) => {
                        const dateStr = format(date, 'yyyy-MM-dd')
                        const dateAvailability = calendarData.availability.find(a => a.date === dateStr)
                        return dateAvailability?.available || false
                      },
                      soldOut: (date) => {
                        const dateStr = format(date, 'yyyy-MM-dd')
                        const dateAvailability = calendarData.availability.find(a => a.date === dateStr)
                        return dateAvailability?.soldOut || false
                      }
                    }}
                    modifiersClassNames={{
                      available: '[&>button]:text-blue-600 [&>button]:font-bold',
                      soldOut: '[&>button]:text-red-600'
                    }}
                    className="rounded-lg border shadow-sm  [--cell-size:--spacing(10.5)]"
                  />
                )}
              </div>
            </div>

            {/* AI Summary Card */}
            <Card className="mt-6">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="size-5 text-primary" />
                    <CardTitle>Reservation Insights</CardTitle>
                  </div>
                  {aiSummary && !loadingAi && (
                    <div className="flex items-center gap-3">
                      {aiLastUpdated && (
                        <span className="text-xs text-muted-foreground">
                          Last updated: {new Date(aiLastUpdated).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit',
                            hour12: true
                          })}
                        </span>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefreshAiSummary}
                        disabled={loadingAi}
                        className="gap-2"
                      >
                        <RefreshCw className="size-4" />
                        Refresh
                      </Button>
                    </div>
                  )}
                </div>
                <CardDescription>
                  AI-powered information about booking this restaurant
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {loadingAi && (
                  <div className="text-center py-6 flex items-center gap-2 justify-center text-muted-foreground">
                    <LoaderCircle className="animate-spin" />
                    <p>Searching for reservation information...</p>
                  </div>
                )}

                {aiError && (
                  <Alert variant="destructive">
                    <AlertCircle className="size-4" />
                    <AlertDescription>{aiError}</AlertDescription>
                  </Alert>
                )}

                {aiSummary && !loadingAi && (
                  <div className="space-y-4">
                    {/* Summary */}
                    <div className="prose prose-sm max-w-none">
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {aiSummary.summary}
                      </p>
                    </div>

                    {/* Show Details Button */}
                    {((aiSummary.groundingChunks && aiSummary.groundingChunks.length > 0) ||
                      (aiSummary.webSearchQueries && aiSummary.webSearchQueries.length > 0)) && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowAiDetails(!showAiDetails)}
                          className="w-full gap-2"
                        >
                          <ChevronDown className={`size-4 transition-transform ${showAiDetails ? 'rotate-180' : ''}`} />
                          {showAiDetails ? 'Hide' : 'Show'} Additional Details
                        </Button>

                        {showAiDetails && (
                          <div className="space-y-4">
                            {/* Grounding Chunks (Sources) */}
                            {aiSummary.groundingChunks && aiSummary.groundingChunks.length > 0 && (
                              <>
                                <Separator />
                                <div>
                                  <p className="text-xs font-medium text-muted-foreground mb-2">
                                    Sources
                                  </p>
                                  <div className="space-y-2">
                                    {aiSummary.groundingChunks.map((chunk, idx) => (
                                      <div key={idx} className="text-xs">
                                        <a
                                          href={chunk.uri || '#'}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="flex items-start gap-2 text-primary hover:underline group"
                                        >
                                          <span className="shrink-0 font-medium">[{idx + 1}]</span>
                                          <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-1">
                                              <span className="font-medium truncate">{chunk.title}</span>
                                              <ExternalLink className="size-3 shrink-0" />
                                            </div>
                                            {chunk.snippet && (
                                              <p className="text-muted-foreground mt-0.5 line-clamp-2">
                                                {chunk.snippet}
                                              </p>
                                            )}
                                          </div>
                                        </a>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </>
                            )}

                            {/* Web Search Queries */}
                            {aiSummary.webSearchQueries && aiSummary.webSearchQueries.length > 0 && (
                              <>
                                <Separator />
                                <div>
                                  <p className="text-xs font-medium text-muted-foreground mb-2">
                                    Search Queries Used
                                  </p>
                                  <div className="flex flex-wrap gap-2">
                                    {aiSummary.webSearchQueries.map((query, idx) => (
                                      <span
                                        key={idx}
                                        className="text-xs bg-secondary px-2 py-1 rounded-md"
                                      >
                                        {query}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Side - Make Reservation */}
          <div>
            {/* Restaurant Photos Carousel */}
            {venuePhoto && venuePhoto.photoUrls && venuePhoto.photoUrls.length > 0 && !loadingPhoto && (
              <div className="mb-6">
                <Carousel className="w-full">
                  <CarouselContent>
                    {venuePhoto.photoUrls.map((photoUrl, index) => (
                      <CarouselItem key={index}>
                        <div className="rounded-lg overflow-hidden border shadow-sm">
                          <img
                            src={photoUrl}
                            alt={`${venueData?.name || 'Restaurant'} - Photo ${index + 1}`}
                            className="w-full h-auto max-w-full object-cover pointer-events-none select-none"
                            style={{ maxHeight: '400px' }}
                            onError={(e) => {
                              // Hide image if it fails to load
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                        </div>
                      </CarouselItem>
                    ))}
                  </CarouselContent>
                  <CarouselPrevious className="left-2" />
                  <CarouselNext className="right-2" />
                </Carousel>
              </div>
            )}

            {loadingPhoto && (
              <div className="mb-6 rounded-lg border shadow-sm bg-muted flex items-center justify-center" style={{ height: '400px' }}>
                <LoaderCircle className="animate-spin size-8 text-muted-foreground" />
              </div>
            )}

            <Card>
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

                {/* Reservation Details */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                          <CalendarIcon className="mr-2 size-4" />
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
                      <Label>Seating Type Preference (optional)</Label>
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
                  disabled={loading || !reservationForm.date}
                  className="w-full"
                >
                  {loading ? 'Processing...' : 'Schedule Reservation'}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}
