import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { format } from "date-fns";
import { TrendingUp, Star, Search } from "lucide-react";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import {
  getTrendingRestaurants,
  getTopRatedRestaurants,
  type TrendingRestaurant,
} from "@/lib/api";
import { useVenue } from "@/contexts/VenueContext";
import { TIME_SLOTS } from "@/lib/time-slots";
import { cn } from "@/lib/utils";
import { RestaurantGridCard } from "@/components/RestaurantGridCard";
import { SearchBar } from "@/components/SearchBar";
import {
  getTrendingRestaurantsCache,
  saveTrendingRestaurantsCache,
  getTopRatedRestaurantsCache,
  saveTopRatedRestaurantsCache,
} from "@/services/firebase";

export function HomePage() {
  const navigate = useNavigate();
  const [trendingRestaurants, setTrendingRestaurants] = useState<
    TrendingRestaurant[]
  >([]);
  const [loadingTrending, setLoadingTrending] = useState(false);
  const [topRatedRestaurants, setTopRatedRestaurants] = useState<
    TrendingRestaurant[]
  >([]);
  const [loadingTopRated, setLoadingTopRated] = useState(false);
  const { reservationForm, setReservationForm } = useVenue();

  const handleSelectVenue = (venueId: string) => {
    navigate(`/venue?id=${venueId}`);
  };

  // Fetch trending restaurants on mount
  useEffect(() => {
    const fetchTrending = async () => {
      setLoadingTrending(true);
      try {
        // Try to get from cache first
        const cachedData = await getTrendingRestaurantsCache();

        if (cachedData) {
          console.log("Using cached trending restaurants");
          setTrendingRestaurants(cachedData);
        } else {
          // Fetch fresh data from API
          console.log("Fetching fresh trending restaurants");
          const data = await getTrendingRestaurants(10);
          setTrendingRestaurants(data);

          // Save to cache
          await saveTrendingRestaurantsCache(data);
        }
      } catch (err) {
        console.error("Failed to fetch trending restaurants:", err);
      } finally {
        setLoadingTrending(false);
      }
    };

    fetchTrending();
  }, []);

  // Fetch top-rated restaurants on mount
  useEffect(() => {
    const fetchTopRated = async () => {
      setLoadingTopRated(true);
      try {
        // Try to get from cache first
        const cachedData = await getTopRatedRestaurantsCache();

        if (cachedData) {
          console.log("Using cached top-rated restaurants");
          setTopRatedRestaurants(cachedData);
        } else {
          // Fetch fresh data from API
          console.log("Fetching fresh top-rated restaurants");
          const data = await getTopRatedRestaurants(10);
          setTopRatedRestaurants(data);

          // Save to cache
          await saveTopRatedRestaurantsCache(data);
        }
      } catch (err) {
        console.error("Failed to fetch top-rated restaurants:", err);
      } finally {
        setLoadingTopRated(false);
      }
    };

    toast("Currently Only Serving NYC", {
      description:
        "I am working to expand to more cities soon after OpenTable integration.",
      position: "bottom-left",
      icon: <div className="size-2 mx-auto bg-blue-500 rounded-full" />,
    });
    fetchTopRated();
  }, []);

  return (
    <div className="h-screen bg-background py-24 overflow-y-auto">
      {/* Main Content - Grid Layout */}
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row gap-8 mb-2">
          {/* Left: Search Section */}
          <div className="max-w-160 w-full lg:pr-16">
            {/* Title */}
            <div className="mb-3">
              <h1 className="text-3xl font-bold tracking-tight mb-2">
                Restaurant Search
              </h1>
              <p className="text-muted-foreground">
                Search for restaurants by name to snipe a reservation
              </p>
            </div>

            {/* Search Bar */}
            <div className="space-y-2 mb-6">
              <SearchBar
                className="relative"
                inputClassName="min-h-12 pr-10 pl-5 py-8"
              />
            </div>

            {/* Reservation Form - One Row */}
            <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              {/* Party Size */}
              <div className="space-y-2">
                <Label>Party Size</Label>
                <Select
                  value={reservationForm.partySize}
                  onValueChange={(value) =>
                    setReservationForm({ ...reservationForm, partySize: value })
                  }
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
              </div>

              {/* Date */}
              <div className="space-y-2">
                <Label>Date</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <button
                      className={cn(
                        "flex h-9 w-full items-center justify-start rounded-md border bg-background px-3 py-2 text-sm shadow-xs ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors",
                        !reservationForm.date && "text-muted-foreground"
                      )}
                    >
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
              </div>

              {/* Time */}
              <div className="space-y-2">
                <Label>Desired Time</Label>
                <Select
                  value={reservationForm.timeSlot}
                  onValueChange={(value) =>
                    setReservationForm({ ...reservationForm, timeSlot: value })
                  }
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
              <p className="text-muted-foreground text-sm">
                Placeholder for graphic
              </p>
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
              <p className="text-muted-foreground">
                Loading trending restaurants...
              </p>
            </div>
          ) : trendingRestaurants.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
              {trendingRestaurants.map((restaurant) => {
                // Determine if we should show placeholder or times
                const hasAllReservationDetails =
                  reservationForm.date &&
                  reservationForm.timeSlot &&
                  reservationForm.partySize;

                console.log("[HomePage - Trending] Rendering restaurant:", {
                  id: restaurant.id,
                  name: restaurant.name,
                  hasAllReservationDetails,
                  showPlaceholder: !hasAllReservationDetails,
                  reservationForm: {
                    date: reservationForm.date,
                    timeSlot: reservationForm.timeSlot,
                    partySize: reservationForm.partySize,
                  },
                });

                return (
                  <RestaurantGridCard
                    key={restaurant.id}
                    id={restaurant.id}
                    name={restaurant.name}
                    type={restaurant.type}
                    priceRange={restaurant.priceRange}
                    location={[
                      restaurant.location.neighborhood,
                      restaurant.location.locality,
                    ]
                      .filter(Boolean)
                      .join(", ")}
                    imageUrl={restaurant.imageUrl}
                    onClick={() => handleSelectVenue(restaurant.id)}
                    showPlaceholder={!hasAllReservationDetails}
                  />
                );
              })}
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
              <p className="text-muted-foreground">
                Loading top-rated restaurants...
              </p>
            </div>
          ) : topRatedRestaurants.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
              {topRatedRestaurants.map((restaurant) => {
                // Determine if we should show placeholder or times
                const hasAllReservationDetails =
                  reservationForm.date &&
                  reservationForm.timeSlot &&
                  reservationForm.partySize;

                return (
                  <RestaurantGridCard
                    key={restaurant.id}
                    id={restaurant.id}
                    name={restaurant.name}
                    type={restaurant.type}
                    priceRange={restaurant.priceRange}
                    location={[
                      restaurant.location.neighborhood,
                      restaurant.location.locality,
                    ]
                      .filter(Boolean)
                      .join(", ")}
                    imageUrl={restaurant.imageUrl}
                    onClick={() => handleSelectVenue(restaurant.id)}
                    showPlaceholder={!hasAllReservationDetails}
                  />
                );
              })}
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
  );
}
