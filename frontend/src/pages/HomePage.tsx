import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { Search, AlertCircle, TrendingUp, Star } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { searchRestaurants, getTrendingRestaurants, getTopRatedRestaurants, getVenuePhoto, type TrendingRestaurant } from '@/lib/api'
import { useVenue } from '@/contexts/VenueContext'
import { TIME_SLOTS } from '@/lib/time-slots'
import { cn } from '@/lib/utils'
import { SearchResultItem } from '@/components/SearchResultItem'
import { RestaurantGridCard } from '@/components/RestaurantGridCard'
import { getTrendingRestaurantsCache, saveTrendingRestaurantsCache, getTopRatedRestaurantsCache, saveTopRatedRestaurantsCache } from '@/services/firebase'

export function HomePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [trendingRestaurants, setTrendingRestaurants] = useState<TrendingRestaurant[]>([])
  const [loadingTrending, setLoadingTrending] = useState(false)
  const [topRatedRestaurants, setTopRatedRestaurants] = useState<TrendingRestaurant[]>([])
  const [loadingTopRated, setLoadingTopRated] = useState(false)
  const [searchPopoverOpen, setSearchPopoverOpen] = useState(false)
  const {
    searchResults,
    setSearchResults,
    searchQuery,
    setSearchQuery,
    reservationForm,
    setReservationForm
  } = useVenue()

  const handleSearchChange = async (value: string) => {
    setSearchQuery(value)

    if (!value.trim()) {
      setSearchResults([])
      setError(null)
      setSearchPopoverOpen(false)
      return
    }

    setLoading(true)
    setError(null)
    setSearchPopoverOpen(true)

    try {
      const results = await searchRestaurants(value)

      // Fetch images for all results
      const resultsWithImages = await Promise.all(
        results.map(async (result) => {
          try {
            const photoData = await getVenuePhoto(result.id, result.name)
            return { ...result, imageUrl: photoData.photoUrl }
          } catch {
            return { ...result, imageUrl: null }
          }
        })
      )

      setSearchResults(resultsWithImages)
      setSearchPopoverOpen(resultsWithImages.length > 0)

      if (resultsWithImages.length === 0) {
        setError('No restaurants found matching your search')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search restaurants')
      setSearchPopoverOpen(false)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectVenue = (venueId: string) => {
    setSearchPopoverOpen(false)
    navigate(`/venue?id=${venueId}`)
  }

  const handleSeeAllResults = () => {
    setSearchPopoverOpen(false)
    navigate('/search-results')
  }

  // Fetch trending restaurants on mount
  useEffect(() => {
    const fetchTrending = async () => {
      setLoadingTrending(true)
      try {
        // Try to get from cache first
        const cachedData = await getTrendingRestaurantsCache()

        if (cachedData) {
          console.log('Using cached trending restaurants')
          setTrendingRestaurants(cachedData)
        } else {
          // Fetch fresh data from API
          console.log('Fetching fresh trending restaurants')
          const data = await getTrendingRestaurants(10)
          setTrendingRestaurants(data)

          // Save to cache
          await saveTrendingRestaurantsCache(data)
        }
      } catch (err) {
        console.error('Failed to fetch trending restaurants:', err)
      } finally {
        setLoadingTrending(false)
      }
    }

    fetchTrending()
  }, [])

  // Fetch top-rated restaurants on mount
  useEffect(() => {
    const fetchTopRated = async () => {
      setLoadingTopRated(true)
      try {
        // Try to get from cache first
        const cachedData = await getTopRatedRestaurantsCache()

        if (cachedData) {
          console.log('Using cached top-rated restaurants')
          setTopRatedRestaurants(cachedData)
        } else {
          // Fetch fresh data from API
          console.log('Fetching fresh top-rated restaurants')
          const data = await getTopRatedRestaurants(10)
          setTopRatedRestaurants(data)

          // Save to cache
          await saveTopRatedRestaurantsCache(data)
        }
      } catch (err) {
        console.error('Failed to fetch top-rated restaurants:', err)
      } finally {
        setLoadingTopRated(false)
      }
    }

    fetchTopRated()
  }, [])


  return (
    <div className="h-screen bg-background pt-32 overflow-y-auto">
      {/* Main Content - Grid Layout */}
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row gap-8 mb-2">
          {/* Left: Search Section */}
          <div className='max-w-160 w-full'>
            {/* Title */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold tracking-tight mb-2">Restaurant Search</h1>
              <p className="text-muted-foreground">
                Search for restaurants by name to snipe a reservation
              </p>
            </div>

          {/* Error Messages */}
          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="size-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Search Bar */}
          <div className="space-y-2 mb-6">
            <Popover open={searchPopoverOpen} onOpenChange={setSearchPopoverOpen}>
              <PopoverTrigger asChild>
                <div className="relative">
                  <Input
                    id="search-query"
                    placeholder="e.g., Carbone, Torrisi"
                    value={searchQuery}
                    onChange={(e) => handleSearchChange(e.target.value)}
                    autoComplete="off"
                    className="min-h-12 pr-10 pl-5 py-8"
                  />
                  <Search className="absolute right-6 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
                </div>
              </PopoverTrigger>
              <PopoverContent
                className="w-[var(--radix-popover-trigger-width)] p-0"
                align="start"
                onOpenAutoFocus={(e) => e.preventDefault()}
              >
                {loading ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    Loading results...
                  </div>
                ) : searchResults.length > 0 ? (
                  <div className="max-h-[400px] overflow-y-auto">
                    {searchResults.slice(0, 5).map((result) => (
                      <SearchResultItem
                        key={result.id}
                        id={result.id}
                        name={result.name}
                        type={result.type}
                        priceRange={result.price_range}
                        location={[result.neighborhood, result.locality, result.region]
                          .filter(Boolean)
                          .filter(item => item !== 'N/A')
                          .join(', ')}
                        imageUrl={result.imageUrl || null}
                        onClick={() => handleSelectVenue(result.id)}
                      />
                    ))}
                    {searchResults.length > 5 && (
                      <div className="p-2 border-t">
                        <Button
                          variant="ghost"
                          className="w-full"
                          onClick={handleSeeAllResults}
                        >
                          See all {searchResults.length} results
                        </Button>
                      </div>
                    )}
                  </div>
                ) : null}
              </PopoverContent>
            </Popover>
          </div>

          {/* Reservation Form - One Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {/* Party Size */}
            <div className="space-y-2">
              <Label>Party Size</Label>
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
            <div className="space-y-2">
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
            <div className="space-y-2">
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

          {/* Right: Placeholder Image */}
          <div className="hidden lg:flex w-full items-center justify-center">
            <div className="w-full h-[350px] bg-muted rounded-lg flex items-center justify-center">
              <p className="text-muted-foreground text-sm">Placeholder for graphic</p>
            </div>
          </div>
        </div>

        {/* Trending Restaurants Grid */}
        <div className="">
          <div className="flex items-center gap-2">
            <TrendingUp className="size-6 text-primary" />
            <h2 className="text-2xl font-bold">Trending Restaurants</h2>
          </div>
          <p className="text-sm pb-6 pt-2 text-muted-foreground">
            Popular restaurants climbing on Resy right now
          </p>

          {loadingTrending ? (
            <div className="flex items-center justify-center h-[400px]">
              <p className="text-muted-foreground">Loading trending restaurants...</p>
            </div>
          ) : trendingRestaurants.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
              {trendingRestaurants.map((restaurant) => (
                <RestaurantGridCard
                  key={restaurant.id}
                  id={restaurant.id}
                  name={restaurant.name}
                  type={restaurant.type}
                  priceRange={restaurant.priceRange}
                  location={[restaurant.location.neighborhood, restaurant.location.locality]
                    .filter(Boolean)
                    .join(', ')}
                  imageUrl={restaurant.imageUrl}
                  onClick={() => handleSelectVenue(restaurant.id)}
                />
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-[400px]">
              <div className="text-center space-y-3">
                <Search className="size-12 text-muted-foreground mx-auto opacity-20" />
                <p className="text-muted-foreground text-lg">
                  No trending restaurants available
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Top Rated Restaurants Grid */}
        <div className="mt-12">
          <div className="flex items-center gap-2">
            <Star className="size-6 text-primary" />
            <h2 className="text-2xl font-bold">Top Rated Restaurants</h2>
          </div>
          <p className="text-sm pb-6 pt-2 text-muted-foreground">
            The highest-rated restaurants on Resy right now
          </p>

          {loadingTopRated ? (
            <div className="flex items-center justify-center h-[400px]">
              <p className="text-muted-foreground">Loading top-rated restaurants...</p>
            </div>
          ) : topRatedRestaurants.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
              {topRatedRestaurants.map((restaurant) => (
                <RestaurantGridCard
                  key={restaurant.id}
                  id={restaurant.id}
                  name={restaurant.name}
                  type={restaurant.type}
                  priceRange={restaurant.priceRange}
                  location={[restaurant.location.neighborhood, restaurant.location.locality]
                    .filter(Boolean)
                    .join(', ')}
                  imageUrl={restaurant.imageUrl}
                  onClick={() => handleSelectVenue(restaurant.id)}
                />
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-[400px]">
              <div className="text-center space-y-3">
                <Star className="size-12 text-muted-foreground mx-auto opacity-20" />
                <p className="text-muted-foreground text-lg">
                  No top-rated restaurants available
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
