import { useState, useMemo, useRef, useEffect } from "react";
import { format } from "date-fns";
import { toast } from "sonner";
import {
  Search,
  Calendar as CalendarIcon,
  ChevronDown,
  MapPin,
  Bookmark,
} from "lucide-react";
import {
  Map,
  MapTileLayer,
  MapMarker,
  MapPopup,
  MapTooltip,
  MapZoomControl,
  MapLocateControl,
} from "@/components/ui/map";
import { Map as LeafletMap } from "leaflet";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { TIME_SLOTS } from "@/lib/time-slots";
import { SearchResultItem } from "@/components/SearchResultItem";
import { searchRestaurantsByMap, getVenueLinks } from "@/lib/api";
import type { SearchPagination, SearchResult } from "@/lib/interfaces";
import { useVenue } from "@/contexts/VenueContext";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationPrevious,
  PaginationNext,
  PaginationEllipsis,
} from "@/components/ui/pagination";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/contexts/AuthContext";

// Mock data for filters
const CUISINES = [
  "All Cuisines",
  "Italian",
  "Japanese",
  "American",
  "French",
  "Chinese",
  "Mexican",
  "Mediterranean",
  "Indian",
  "Thai",
  "Korean",
  "Spanish",
  "Greek",
  "Vietnamese",
];

const PRICE_RANGES = [
  { label: "All Prices", value: "all" },
  { label: "$", value: "1" },
  { label: "$$", value: "2" },
  { label: "$$$", value: "3" },
  { label: "$$$$", value: "4" },
];

interface SearchFilters {
  query: string;
  cuisines: string[];
  priceRanges: string[];
  bookmarkedOnly: boolean;
  availableOnly: boolean;
  notReleasedOnly: boolean;
}

export function SearchPage() {
  const { reservationForm, setReservationForm } = useVenue();

  const [filters, setFilters] = useState<SearchFilters>({
    query: "",
    cuisines: [],
    priceRanges: [],
    bookmarkedOnly: false,
    availableOnly: false,
    notReleasedOnly: false,
  });

  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [hoveredVenueId, setHoveredVenueId] = useState<string | null>(null);
  const [pagination, setPagination] = useState<SearchPagination | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [inputsHaveChanged, setInputsHaveChanged] = useState(true); // Track if inputs have changed since last search
  const [activeTab, setActiveTab] = useState<string>("browse"); // Track which tab is active
  const auth = useAuth();
  const mapRef = useRef<LeafletMap | null>(null);

  // Client-side cache for paginated results
  interface CachedPage {
    results: SearchResult[];
    pagination: SearchPagination;
  }
  // Use Record instead of Map to avoid conflict with Leaflet Map import
  const pageCache = useRef<Record<string, CachedPage>>({});
  const currentSearchKey = useRef<string>("");

  // Determine if there's a next page based on backend's hasMore field
  const hasNextPage = useMemo(() => {
    return pagination?.hasMore ?? false;
  }, [pagination]);

  // Manhattan center coordinates (for Leaflet: [lat, lng])
  const mapCenter = useMemo(() => [40.7589, -73.9851] as [number, number], []);

  // Get positions for each venue - only use real coordinates from API
  const venuePositions = useMemo(() => {
    const positions: Record<string, [number, number]> = {};
    searchResults.forEach((result) => {
      // Only include venues with real coordinates
      if (result.latitude != null && result.longitude != null) {
        positions[result.id] = [result.latitude, result.longitude];
      }
    });
    return positions;
  }, [searchResults]);

  // Handle map movement - re-enable search buttons
  const handleMapMove = () => {
    setInputsHaveChanged(true);
  };

  useEffect(() => {
    setInputsHaveChanged(true);
    console.log("Filters:", filters);
    // Clear cache when filters change (new search)
    pageCache.current = {};
    currentSearchKey.current = "";
  }, [filters, reservationForm, activeTab]);

  // Add map event listener for movement - wait for map to be ready
  useEffect(() => {
    let mapInstance: LeafletMap | null = null;

    // Use a timeout to ensure map is fully initialized
    const timer = setTimeout(() => {
      mapInstance = mapRef.current;
      if (mapInstance) {
        mapInstance.on("moveend", handleMapMove);
        mapInstance.on("zoomend", handleMapMove);
      }
    }, 100);

    return () => {
      clearTimeout(timer);
      if (mapInstance) {
        mapInstance.off("moveend", handleMapMove);
        mapInstance.off("zoomend", handleMapMove);
      }
    };
  }, []);

  // Unified search function - uses map bounds for all searches
  const handleSearch = async (page: number = 1) => {
    if (!mapRef.current) return;

    // Validate availableOnly or notReleasedOnly requirements
    if (
      (filters.availableOnly || filters.notReleasedOnly) &&
      activeTab === "browse"
    ) {
      const missing = [];
      if (!reservationForm.partySize) missing.push("party size");
      if (!reservationForm.date) missing.push("date");
      if (!reservationForm.timeSlot) missing.push("desired time");

      if (missing.length > 0) {
        const filterType = filters.availableOnly
          ? "available restaurants"
          : "not released restaurants";
        toast.error(
          `Please fill in ${missing.join(
            ", "
          )} to search for ${filterType} only`
        );
        return;
      }
    }

    const map = mapRef.current;
    const bounds = map.getBounds();
    let sw = bounds.getSouthWest();
    let ne = bounds.getNorthEast();

    // Check if coordinates are identical (happens on mobile when map is hidden)
    if (sw.lat === ne.lat && sw.lng === ne.lng) {
      console.log(
        "[MAP SEARCH] Detected identical coordinates (mobile), using default NYC bounds"
      );
      // Default NYC bounding box covering Manhattan area
      sw = { lat: 40.7, lng: -74.02 } as L.LatLng;
      ne = { lat: 40.8, lng: -73.93 } as L.LatLng;
    }

    // Calculate offset from page number
    const offset = (page - 1) * 20;

    // Skip cuisine and price filters when on "specific" tab (specific restaurant search)
    // Skip query filter when on "browse" tab (browsing restaurants)
    const shouldApplyFilters = activeTab !== "specific";
    const shouldApplyQuery = activeTab === "specific";

    // Generate cache key based on search parameters
    const searchKey = JSON.stringify({
      swLat: sw.lat.toFixed(4),
      swLng: sw.lng.toFixed(4),
      neLat: ne.lat.toFixed(4),
      neLng: ne.lng.toFixed(4),
      query: shouldApplyQuery ? filters.query.trim() : "",
      cuisines: shouldApplyFilters ? filters.cuisines.sort() : [],
      priceRanges: shouldApplyFilters ? filters.priceRanges.sort() : [],
      availableOnly: filters.availableOnly && activeTab === "browse",
      notReleasedOnly: filters.notReleasedOnly && activeTab === "browse",
      day: reservationForm.date
        ? format(reservationForm.date, "yyyy-MM-dd")
        : "",
      partySize: reservationForm.partySize || "",
      desiredTime: reservationForm.timeSlot || "",
      activeTab,
    });

    const cacheKey = `${searchKey}-page${page}`;

    // Check cache first
    if (pageCache.current[cacheKey]) {
      console.log("[SearchPage] Using cached results for page", page);
      const cached = pageCache.current[cacheKey];
      setSearchResults(cached.results);
      setPagination(cached.pagination);
      setCurrentPage(page);
      setHasSearched(true);
      return;
    }

    setLoading(true);
    setHasSearched(true);
    setCurrentPage(page);
    console.log("[SearchPage] Starting search - disabling buttons");
    setInputsHaveChanged(false); // Disable buttons after search

    try {
      console.log("[SearchPage] Search filters:", {
        activeTab,
        shouldApplyFilters,
        shouldApplyQuery,
        query: filters.query,
        cuisines: filters.cuisines,
        priceRanges: filters.priceRanges,
        availableOnly: filters.availableOnly,
        notReleasedOnly: filters.notReleasedOnly,
        willApplyQuery: shouldApplyQuery && filters.query.trim(),
        willApplyCuisines: shouldApplyFilters && filters.cuisines.length > 0,
        willApplyPriceRanges:
          shouldApplyFilters && filters.priceRanges.length > 0,
      });

      const apiParams = {
        swLat: sw.lat,
        swLng: sw.lng,
        neLat: ne.lat,
        neLng: ne.lng,
        query: shouldApplyQuery ? filters.query.trim() || undefined : undefined,
        cuisines:
          shouldApplyFilters && filters.cuisines.length > 0
            ? filters.cuisines
            : undefined,
        priceRanges:
          shouldApplyFilters && filters.priceRanges.length > 0
            ? filters.priceRanges
            : undefined,
        offset,
        perPage: 20,
        availableOnly: filters.availableOnly && activeTab === "browse",
        notReleasedOnly: filters.notReleasedOnly && activeTab === "browse",
        // Always send day and partySize if provided (for availability fetching)
        day: reservationForm.date
          ? format(reservationForm.date, "yyyy-MM-dd")
          : undefined,
        partySize: reservationForm.partySize || undefined,
        desiredTime: reservationForm.timeSlot || undefined,
      };

      console.log("[SearchPage] API call parameters:", apiParams);

      const user = auth.currentUser;
      const userId = user!.uid;
      const response = await searchRestaurantsByMap(userId, apiParams);

      // Fetch venue data (type/cuisine + image) for all results using venue-links endpoint
      const resultsWithVenueData = await Promise.all(
        response.results.map(async (result) => {
          try {
            // Use the Cloud Function API to get venue links and data
            const venueLinksData = await getVenueLinks(userId, result.id);

            // Update result with type from venue details
            return {
              ...result,
              type: venueLinksData.venueData?.type || result.type,
              imageUrl: result.imageUrl, // Use imageUrl from search results
            };
          } catch (error) {
            console.error(
              `Failed to fetch venue links for ${result.id}:`,
              error
            );
            // Fallback: return result as-is
            return { ...result };
          }
        })
      );

      console.log("Search results:", resultsWithVenueData);
      console.log(
        "[SearchPage] First result availableTimes:",
        resultsWithVenueData[0]?.availableTimes
      );

      setSearchResults(resultsWithVenueData);
      setPagination(response.pagination);

      // Cache the results for this page
      pageCache.current[cacheKey] = {
        results: resultsWithVenueData,
        pagination: response.pagination,
      };
      console.log("[SearchPage] Cached results for", cacheKey);

      console.log("[SearchPage] Search complete:", {
        resultsCount: resultsWithVenueData.length,
        pagination: response.pagination,
        paginationTotal: response.pagination.total,
        paginationHasTotal: "total" in response.pagination,
        cacheSize: Object.keys(pageCache.current).length,
      });
    } catch (err) {
      console.error("Map search error:", err);
      setSearchResults([]);
      setPagination(null);
    } finally {
      setLoading(false);
    }
  };

  // Helper functions
  const handleCardClick = (venueId: string) => {
    window.open(`/venue?id=${venueId}`, "_blank");
  };

  const handleCardHover = (venueId: string | null) => {
    setHoveredVenueId(venueId);
  };

  // Pagination handler - just calls search with new page
  const handlePageChange = (page: number) => {
    handleSearch(page);
  };

  const selectedCuisines = useMemo(() => {
    if (filters.cuisines.length === 0) return "All Cuisines";

    if (filters.cuisines.length === 1) {
      return filters.cuisines[0] || "All Cuisines";
    }

    // Show like "Italian, Japanese"
    return filters.cuisines.filter((c) => c && CUISINES.includes(c)).join(", ");
  }, [filters.cuisines]);

  const selectedPriceRangeLabels = useMemo(() => {
    if (filters.priceRanges.length === 0) return "All Prices";
    if (filters.priceRanges.length === 1) {
      return (
        PRICE_RANGES.find((p) => p.value === filters.priceRanges[0])?.label ||
        "All Prices"
      );
    }
    // Show like "$, $$$"
    return filters.priceRanges
      .map((val) => PRICE_RANGES.find((p) => p.value === val)?.label)
      .filter(Boolean)
      .join(", ");
  }, [filters.priceRanges]);

  return (
    <div className="h-screen bg-background pt-19 flex flex-col overflow-hidden">
      <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="flex-1 flex gap-0 min-h-0 max-h-full overflow-hidden">
          {/* Left Side - Search Filters and Results */}
          <div className="flex flex-col w-full md:w-auto md:min-w-[500px] md:max-w-[600px] mx-auto md:mx-0 gap-6 px-4 py-8 mb-16 h-full overflow-y-auto flex-1 min-h-0 no-scrollbar">
            {/* Search Filters Card */}
            <Card className="p-2">
              <CardContent className="p-6">
                <Tabs
                  defaultValue="browse"
                  className="w-full"
                  onValueChange={(value) => setActiveTab(value)}
                >
                  <TabsList className="grid w-full grid-cols-2 mb-6">
                    <TabsTrigger value="browse">Browse Restaurants</TabsTrigger>
                    <TabsTrigger value="specific">
                      Specific Restaurant
                    </TabsTrigger>
                  </TabsList>

                  {/* Tab: Specific Restaurant Search */}
                  <TabsContent value="specific" className="space-y-6">
                    {/* Res Details */}
                    <div className="grid grid-cols-3 gap-4">
                      {/* Party Size - Global State */}
                      <div className="space-y-2">
                        <Label>Party Size</Label>
                        <Select
                          value={reservationForm.partySize}
                          onValueChange={(value) =>
                            setReservationForm({
                              ...reservationForm,
                              partySize: value,
                            })
                          }
                        >
                          <SelectTrigger id="party-size">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {Array.from({ length: 6 }, (_, i) => i + 1).map(
                              (size) => (
                                <SelectItem key={size} value={size.toString()}>
                                  {size} {size === 1 ? "person" : "people"}
                                </SelectItem>
                              )
                            )}
                          </SelectContent>
                        </Select>
                      </div>

                      {/* Date - Global State */}
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
                              <CalendarIcon className="mr-2 size-4" />
                              {reservationForm.date ? (
                                format(reservationForm.date, "MMM d, yyyy")
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

                      {/* Time - Global State */}
                      <div className="space-y-2">
                        <Label>Desired Time</Label>
                        <Select
                          value={reservationForm.timeSlot}
                          onValueChange={(value) =>
                            setReservationForm({
                              ...reservationForm,
                              timeSlot: value,
                            })
                          }
                        >
                          <SelectTrigger id="time">
                            <SelectValue />
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

                    <div className="space-y-2">
                      <Label htmlFor="search-query">Restaurant Name</Label>
                      <div className="relative">
                        <Input
                          id="search-query"
                          placeholder="e.g., Carbone, Torrisi"
                          value={filters.query}
                          onChange={(e) =>
                            setFilters({ ...filters, query: e.target.value })
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              handleSearch(1);
                            }
                          }}
                          className="pr-10"
                        />
                        <Search className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                      </div>
                    </div>

                    <div className="w-full">
                      <div className="flex items-center gap-2 mx-auto w-max">
                        <div className="flex items-center space-x-2">
                          <Button
                            id="available-browse"
                            variant={
                              filters.availableOnly ? "secondary" : "outline"
                            }
                            size="sm"
                            className="border active:bg-black/8"
                            onClick={() =>
                              setFilters({
                                ...filters,
                                availableOnly: !filters.availableOnly,
                                notReleasedOnly: false, // Disable notReleasedOnly when enabling availableOnly
                              })
                            }
                          >
                            Available Reservations Only
                          </Button>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Button
                            id="not-released-browse"
                            variant={
                              filters.notReleasedOnly ? "secondary" : "outline"
                            }
                            size="sm"
                            className="border active:bg-black/8"
                            onClick={() =>
                              setFilters({
                                ...filters,
                                notReleasedOnly: !filters.notReleasedOnly,
                                availableOnly: false, // Disable availableOnly when enabling notReleasedOnly
                              })
                            }
                          >
                            Not Released Yet Only
                          </Button>
                        </div>
                      </div>
                    </div>

                    <Button
                      onClick={() => {
                        handleSearch(1);
                      }}
                      disabled={loading || filters.query.trim() === ""}
                      className="w-full mb-0"
                    >
                      {loading ? "Searching..." : "Search Restaurants"}
                    </Button>
                  </TabsContent>

                  {/* Tab: Browse Restaurants */}
                  <TabsContent value="browse" className="space-y-6">
                    {/* Reservation Inputs */}
                    <div className="grid grid-cols-3 gap-4">
                      {/* Party Size - Global State */}
                      <div className="space-y-2">
                        <Label>Party Size</Label>
                        <Select
                          value={reservationForm.partySize}
                          onValueChange={(value) =>
                            setReservationForm({
                              ...reservationForm,
                              partySize: value,
                            })
                          }
                        >
                          <SelectTrigger id="party-size-browse">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {Array.from({ length: 6 }, (_, i) => i + 1).map(
                              (size) => (
                                <SelectItem key={size} value={size.toString()}>
                                  {size} {size === 1 ? "person" : "people"}
                                </SelectItem>
                              )
                            )}
                          </SelectContent>
                        </Select>
                      </div>

                      {/* Date - Global State */}
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
                              <CalendarIcon className="mr-2 size-4" />
                              {reservationForm.date ? (
                                format(reservationForm.date, "MMM d, yyyy")
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

                      {/* Time - Global State */}
                      <div className="space-y-2">
                        <Label>Desired Time</Label>
                        <Select
                          value={reservationForm.timeSlot}
                          onValueChange={(value) =>
                            setReservationForm({
                              ...reservationForm,
                              timeSlot: value,
                            })
                          }
                        >
                          <SelectTrigger id="time-browse">
                            <SelectValue />
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

                    <div className="grid grid-cols-2 gap-4">
                      {/* Cuisine Multi-Select */}
                      <div>
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              className="w-full justify-between overflow-hidden"
                            >
                              <span className="truncate">
                                {selectedCuisines}
                              </span>
                              <ChevronDown className="ml-2 size-4 opacity-50 shrink-0" />
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent
                            className="w-[200px] p-0"
                            align="start"
                          >
                            <div className="max-h-[300px] overflow-y-auto p-2">
                              {CUISINES.filter((c) => c !== "All Cuisines").map(
                                (cuisine) => (
                                  <div
                                    key={cuisine}
                                    className="flex items-center space-x-2 hover:bg-accent rounded-sm"
                                  >
                                    <Checkbox
                                      id={`cuisine-browse-${cuisine}`}
                                      checked={filters.cuisines.includes(
                                        cuisine
                                      )}
                                      onCheckedChange={(checked) => {
                                        if (checked) {
                                          setFilters({
                                            ...filters,
                                            cuisines: [
                                              ...filters.cuisines,
                                              cuisine,
                                            ],
                                          });
                                        } else {
                                          setFilters({
                                            ...filters,
                                            cuisines: filters.cuisines.filter(
                                              (c) => c !== cuisine
                                            ),
                                          });
                                        }
                                      }}
                                      className="ml-2"
                                    />
                                    <label
                                      htmlFor={`cuisine-browse-${cuisine}`}
                                      className="text-sm p-2 cursor-pointer flex-1 hover:bg-accent rounded-sm"
                                    >
                                      {cuisine}
                                    </label>
                                  </div>
                                )
                              )}
                            </div>
                          </PopoverContent>
                        </Popover>
                      </div>

                      {/* Price Range Multi-Select */}
                      <div>
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              className="w-full justify-between overflow-hidden"
                            >
                              <span className="truncate">
                                {selectedPriceRangeLabels}
                              </span>
                              <ChevronDown className="ml-2 size-4 opacity-50 shrink-0" />
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent
                            className="w-[200px] p-0"
                            align="start"
                          >
                            <div className="max-h-[300px] overflow-y-auto p-2">
                              {PRICE_RANGES.filter(
                                (p) => p.value !== "all"
                              ).map((price) => (
                                <div
                                  key={price.value}
                                  className="flex items-center space-x-2 hover:bg-accent rounded-sm"
                                >
                                  <Checkbox
                                    id={`price-browse-${price.value}`}
                                    checked={filters.priceRanges.includes(
                                      price.value
                                    )}
                                    onCheckedChange={(checked) => {
                                      if (checked) {
                                        setFilters({
                                          ...filters,
                                          priceRanges: [
                                            ...filters.priceRanges,
                                            price.value,
                                          ],
                                        });
                                      } else {
                                        setFilters({
                                          ...filters,
                                          priceRanges:
                                            filters.priceRanges.filter(
                                              (p) => p !== price.value
                                            ),
                                        });
                                      }
                                    }}
                                    className="ml-2"
                                  />
                                  <label
                                    htmlFor={`price-browse-${price.value}`}
                                    className="text-sm cursor-pointer flex-1 p-2 hover:bg-accent rounded-sm"
                                  >
                                    {price.label}
                                  </label>
                                </div>
                              ))}
                            </div>
                          </PopoverContent>
                        </Popover>
                      </div>
                    </div>

                    <div className="w-full">
                      <div className="flex items-center w-full">
                        <div className="flex flex-wrap gap-2 w-max mx-auto">
                          <div className="flex items-center space-x-2">
                            <Button
                              id="available-browse"
                              variant={
                                filters.availableOnly ? "secondary" : "outline"
                              }
                              size="sm"
                              className="border active:bg-black/8"
                              onClick={() =>
                                setFilters({
                                  ...filters,
                                  availableOnly: !filters.availableOnly,
                                  notReleasedOnly: false, // Disable notReleasedOnly when enabling availableOnly
                                })
                              }
                            >
                              Available Reservations Only
                            </Button>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Button
                              id="not-released-browse"
                              variant={
                                filters.notReleasedOnly
                                  ? "secondary"
                                  : "outline"
                              }
                              size="sm"
                              className="border active:bg-black/8"
                              onClick={() =>
                                setFilters({
                                  ...filters,
                                  notReleasedOnly: !filters.notReleasedOnly,
                                  availableOnly: false, // Disable availableOnly when enabling notReleasedOnly
                                })
                              }
                            >
                              Not Released Yet Only
                            </Button>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Button
                              id="bookmarked-browse"
                              variant={
                                filters.bookmarkedOnly ? "secondary" : "outline"
                              }
                              size="sm"
                              className="border active:bg-black/8"
                              onClick={() =>
                                setFilters({
                                  ...filters,
                                  bookmarkedOnly: !filters.bookmarkedOnly,
                                })
                              }
                            >
                              <Bookmark className="size-4" /> Only
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>

                    <Button
                      onClick={() => {
                        console.log(
                          "[SearchPage] Search button (Browse) clicked, inputsHaveChanged:",
                          inputsHaveChanged
                        );
                        handleSearch(1);
                      }}
                      disabled={loading || !inputsHaveChanged}
                      className="w-full mb-0"
                    >
                      {loading ? "Searching..." : "Search Restaurants"}
                    </Button>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            {/* Results */}
            <div className="flex-1 min-h-0">
              {loading && (
                <div className="text-center py-8 text-muted-foreground">
                  Loading results...
                </div>
              )}

              {!loading && hasSearched && searchResults.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No restaurants found. Try a different search.
                  {currentPage > 1 && (
                    <div className="mt-2">
                      <Button
                        variant="outline"
                        onClick={() => handlePageChange(1)}
                      >
                        Go back to first page
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {!loading && searchResults.length > 0 && (
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground mb-4">
                    Found {pagination?.total || searchResults.length} restaurant
                    {(pagination?.total || searchResults.length) !== 1
                      ? "s"
                      : ""}
                    {pagination && (currentPage > 1 || hasNextPage) && (
                      <span> (Page {currentPage})</span>
                    )}
                  </p>
                  <div className={`${!pagination ? "pb-16" : ""} space-y-2`}>
                    {searchResults.map((result) => {
                      // For showing placeholder: need all reservation details (date, time, party size)
                      const hasAllReservationDetails =
                        reservationForm.date &&
                        reservationForm.timeSlot &&
                        reservationForm.partySize;

                      // For showing available times: only need date and party size (backend fetches with these)
                      const hasAvailabilityParams =
                        reservationForm.date && reservationForm.partySize;

                      return (
                        <div className="mb-0">
                          <SearchResultItem
                            key={result.id}
                            id={result.id}
                            name={result.name}
                            type={result.type}
                            priceRange={result.price_range}
                            location={[
                              result.neighborhood,
                              result.locality,
                              result.region,
                            ]
                              .filter(Boolean)
                              .filter((item) => item !== "N/A")
                              .join(", ")}
                            imageUrl={result.imageUrl || null}
                            onClick={() => handleCardClick(result.id)}
                            onMouseEnter={() => handleCardHover(result.id)}
                            onMouseLeave={() => handleCardHover(null)}
                            showPlaceholder={!hasAllReservationDetails}
                            availableTimes={
                              hasAvailabilityParams
                                ? result.availableTimes
                                : undefined
                            }
                            availabilityStatus={
                              hasAvailabilityParams
                                ? result.availabilityStatus
                                : undefined
                            }
                          />
                          <Separator className="my-2" />
                        </div>
                      );
                    })}
                  </div>

                  {/* Pagination Controls */}
                  {pagination && (currentPage > 1 || hasNextPage) && (
                    <Pagination className="mt-6 pb-16">
                      <PaginationContent>
                        <PaginationItem>
                          <PaginationPrevious
                            href="#"
                            onClick={(e) => {
                              e.preventDefault();
                              if (currentPage > 1) {
                                handlePageChange(currentPage - 1);
                              }
                            }}
                            className={
                              currentPage === 1
                                ? "pointer-events-none opacity-50"
                                : ""
                            }
                          />
                        </PaginationItem>

                        {/* Current Page Number */}
                        <PaginationItem>
                          <PaginationLink
                            href="#"
                            onClick={(e) => e.preventDefault()}
                            isActive={true}
                          >
                            {currentPage}
                          </PaginationLink>
                        </PaginationItem>

                        {hasNextPage && (
                          <PaginationItem>
                            <PaginationEllipsis />
                          </PaginationItem>
                        )}

                        <PaginationItem>
                          <PaginationNext
                            href="#"
                            onClick={(e) => {
                              e.preventDefault();
                              if (hasNextPage) {
                                handlePageChange(currentPage + 1);
                              }
                            }}
                            className={
                              !hasNextPage
                                ? "pointer-events-none opacity-50"
                                : ""
                            }
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  )}
                </div>
              )}

              {!loading && !hasSearched && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center space-y-3">
                    <Search className="size-12 mx-auto text-muted-foreground" />
                    <h3 className="text-lg font-medium">
                      Search for Restaurants
                    </h3>
                    <p className="text-sm text-muted-foreground max-w-sm">
                      Enter a restaurant name and customize your filters to find
                      the perfect dining experience in NYC
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Side - Leaflet Map */}
          <div className="hidden md:flex flex-1 relative overflow-hidden">
            {activeTab === "browse" && (
              <>
                {/* Search Here Button - Overlaid on map */}
                <div className="absolute top-6 left-1/2 -translate-x-1/2 z-1000 flex flex-col items-center gap-1">
                  <Button
                    onClick={() => {
                      console.log(
                        "[SearchPage] Search This Area button clicked, inputsHaveChanged:",
                        inputsHaveChanged
                      );
                      handleSearch(1);
                    }}
                    disabled={loading || !inputsHaveChanged}
                    className="shadow-lg"
                  >
                    {loading ? "Searching..." : "Search This Area"}
                  </Button>
                </div>
              </>
            )}

            <Map
              center={mapCenter}
              zoom={13}
              className="h-full w-full"
              ref={mapRef}
            >
              <MapTileLayer />
              {searchResults.map((result) => {
                const position = venuePositions[result.id];

                // Skip venues without coordinates
                if (!position) return null;

                const isHovered = hoveredVenueId === result.id;

                return (
                  <MapMarker
                    key={result.id}
                    position={position}
                    icon={
                      <MapPin
                        className={`
                            transition-transform duration-300 ease-in-out
                            ${
                              isHovered
                                ? "text-blue-600 fill-blue-600 scale-125"
                                : "text-black fill-black scale-100"
                            }
                          `}
                      />
                    }
                  >
                    <MapTooltip side="top">
                      <div className="font-medium">{result.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {result.neighborhood || "Manhattan"}
                      </div>
                    </MapTooltip>
                    <MapPopup>
                      <div className="flex flex-col gap-2 items-start">
                        <div className="font-semibold text-lg">
                          {result.name}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {result.neighborhood || "Manhattan"}
                        </div>
                        <Button
                          size="sm"
                          onClick={() =>
                            window.open(`/venue?id=${result.id}`, "_blank")
                          }
                        >
                          Reserve
                        </Button>
                      </div>
                    </MapPopup>
                  </MapMarker>
                );
              })}
              <MapZoomControl className="top-auto left-1 bottom-13 right-auto" />
              <MapLocateControl className="top-auto right-1 bottom-13 left-auto" />
            </Map>
          </div>
        </div>
      </main>
    </div>
  );
}
