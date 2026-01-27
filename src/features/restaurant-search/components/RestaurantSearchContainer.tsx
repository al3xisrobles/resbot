import React, {
    useState,
    useMemo,
    useRef,
    useEffect,
    useCallback,
} from "react";
import { format } from "date-fns";
import { toast } from "sonner";
import { MapPin } from "lucide-react";
import * as L from "leaflet";
import { renderToString } from "react-dom/server";
import { Button } from "@/components/ui/button";
import { searchRestaurantsByMap, getTrendingRestaurants, getTopRatedRestaurants } from "@/lib/api";
import type { SearchPagination, SearchResult } from "@/lib/interfaces";
import { useAuth } from "@/contexts/AuthContext";
import { useAtom } from "jotai";
import { reservationFormAtom } from "@/atoms/reservationAtoms";
import { cityConfigAtom } from "@/atoms/cityAtom";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { Stack } from "@/components/ui/layout";
import { SearchSidebar } from "./SearchSidebar";
import { MapView } from "./MapView.private";
import type { SearchFilters, SearchMode } from "../lib/types";
import { Map as LeafletMap, Marker as LeafletMarkerType } from "leaflet";

// Pre-create icon instances to avoid recreating on every render
const createIcon = (isHovered: boolean) =>
    L.divIcon({
        html: renderToString(
            <MapPin
                className={`size-6 transition-transform duration-300 ease-in-out ${isHovered
                    ? "text-blue-600 fill-blue-600 scale-125"
                    : "text-black fill-black scale-100"
                    }`}
            />
        ),
        iconAnchor: [12, 12],
        className: "",
    });

// Cache icons to avoid recreating them
const defaultIcon = createIcon(false);
const hoveredIcon = createIcon(true);

export function RestaurantSearchContainer() {
    const [reservationForm] = useAtom(reservationFormAtom);
    const cityConfig = useAtom(cityConfigAtom)[0];

    const [filters, setFilters] = useState<SearchFilters>({
        query: "",
        cuisines: [],
        priceRanges: [],
        bookmarkedOnly: false,
        availableOnly: false,
        notReleasedOnly: false,
        mode: "browse",
    });

    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(true); // Start with loading true to show skeletons immediately
    const [hasSearched, setHasSearched] = useState(false);
    const [hoveredVenueId, setHoveredVenueId] = useState<string | null>(null);
    const [pagination, setPagination] = useState<SearchPagination | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [inputsHaveChanged, setInputsHaveChanged] = useState(true);
    const auth = useAuth();
    const mapRef = useRef<LeafletMap | null>(null);

    const markerRefsMap = useRef<globalThis.Map<string, LeafletMarkerType>>(
        new globalThis.Map()
    );
    const prevHoveredIdRef = useRef<string | null>(null);

    // Imperative hover effect
    useEffect(() => {
        if (
            prevHoveredIdRef.current &&
            prevHoveredIdRef.current !== hoveredVenueId
        ) {
            const prevMarker = markerRefsMap.current.get(prevHoveredIdRef.current);
            if (prevMarker) {
                prevMarker.setIcon(defaultIcon);
            }
        }

        if (hoveredVenueId) {
            const marker = markerRefsMap.current.get(hoveredVenueId);
            if (marker) {
                marker.setIcon(hoveredIcon);
            }
        }

        prevHoveredIdRef.current = hoveredVenueId;
    }, [hoveredVenueId]);

    interface CachedPage {
        results: SearchResult[];
        pagination: SearchPagination;
    }
    const pageCache = useRef<Record<string, CachedPage>>({});
    const currentSearchKey = useRef<string>("");

    const hasNextPage = useMemo(() => {
        return pagination?.hasMore ?? false;
    }, [pagination]);

    const mapCenter = useMemo(
        () => cityConfig.center as [number, number],
        [cityConfig.center]
    );

    const handleMapMove = () => {
        setInputsHaveChanged(true);
    };

    useEffect(() => {
        setInputsHaveChanged(true);
        console.log("Filters:", filters);
        pageCache.current = {};
        currentSearchKey.current = "";
    }, [filters, reservationForm]);

    // Recenter map when city changes
    useEffect(() => {
        const mapInstance = mapRef.current;
        if (mapInstance) {
            mapInstance.setView(cityConfig.center, mapInstance.getZoom());
            // Clear search results when city changes
            setSearchResults([]);
            setHasSearched(false);
            pageCache.current = {};
            currentSearchKey.current = "";
        }
    }, [cityConfig]);

    useEffect(() => {
        let mapInstance: LeafletMap | null = null;

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

    // Auto-search with debounce when filters or reservation form changes
    useEffect(() => {
        // Set loading immediately when filters change
        setLoading(true);
        
        const timer = setTimeout(() => {
            if (mapRef.current) {
                handleSearch(1);
            }
        }, 500); // 500ms debounce

        return () => clearTimeout(timer);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters, reservationForm]);

    const handleSearch = async (page: number = 1) => {
        if (!mapRef.current) return;

        // Skip map search if mode is trending or top-rated (handled by handleModeChange)
        if (filters.mode === "trending" || filters.mode === "top-rated") {
            return;
        }

        if (filters.availableOnly || filters.notReleasedOnly) {
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

        if (sw.lat === ne.lat && sw.lng === ne.lng) {
            console.log(
                `[MAP SEARCH] Detected identical coordinates (mobile), using default ${cityConfig.name} bounds`
            );
            sw = { lat: cityConfig.bounds.sw[0], lng: cityConfig.bounds.sw[1] } as L.LatLng;
            ne = { lat: cityConfig.bounds.ne[0], lng: cityConfig.bounds.ne[1] } as L.LatLng;
        }

        const offset = (page - 1) * 20;

        const searchKey = JSON.stringify({
            swLat: sw.lat.toFixed(4),
            swLng: sw.lng.toFixed(4),
            neLat: ne.lat.toFixed(4),
            neLng: ne.lng.toFixed(4),
            query: "",
            cuisines: filters.cuisines.sort(),
            priceRanges: filters.priceRanges.sort(),
            availableOnly: filters.availableOnly,
            notReleasedOnly: filters.notReleasedOnly,
            day: reservationForm.date
                ? format(reservationForm.date, "yyyy-MM-dd")
                : "",
            partySize: reservationForm.partySize || "",
            desiredTime: reservationForm.timeSlot || "",
        });

        const cacheKey = `${searchKey}-page${page}`;

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
        setInputsHaveChanged(false);

        try {
            console.log("[SearchPage] Search filters:", {
                cuisines: filters.cuisines,
                priceRanges: filters.priceRanges,
                availableOnly: filters.availableOnly,
                notReleasedOnly: filters.notReleasedOnly,
                willApplyCuisines: filters.cuisines.length > 0,
                willApplyPriceRanges: filters.priceRanges.length > 0,
            });

            const apiParams = {
                swLat: sw.lat,
                swLng: sw.lng,
                neLat: ne.lat,
                neLng: ne.lng,
                query: undefined,
                cuisines:
                    filters.cuisines.length > 0 ? filters.cuisines : undefined,
                priceRanges:
                    filters.priceRanges.length > 0 ? filters.priceRanges : undefined,
                offset,
                perPage: 20,
                availableOnly: filters.availableOnly,
                notReleasedOnly: filters.notReleasedOnly,
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
            const results = response.results;

            console.log("Search results:", results);
            console.log(
                "[SearchPage] First result availableTimes:",
                results[0]?.availableTimes
            );

            setSearchResults(results);
            setPagination(response.pagination);

            pageCache.current[cacheKey] = {
                results: results,
                pagination: response.pagination,
            };
            console.log("[SearchPage] Cached results for", cacheKey);
            console.log("[SearchPage] Search complete:", {
                resultsCount: results.length,
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

    const handleCardClick = useCallback((venueId: string) => {
        window.open(`/venue?id=${venueId}`, "_blank");
    }, []);

    const handleCardHover = useCallback((venueId: string | null) => {
        setHoveredVenueId(venueId);
    }, []);

    const handleModeChange = useCallback(async (mode: SearchMode) => {
        if (mode === "trending" || mode === "top-rated") {
            setLoading(true);
            setHasSearched(true);
            try {
                const fetchFn = mode === "trending" ? getTrendingRestaurants : getTopRatedRestaurants;
                const user = auth.currentUser;
                const restaurants = await fetchFn(user?.uid, 20, cityConfig.id);

                // Convert TrendingRestaurant[] to SearchResult[]
                const results: SearchResult[] = restaurants
                    .filter(r => r.lat != null && r.lng != null)
                    .map(r => ({
                        id: r.id,
                        name: r.name,
                        type: r.type,
                        price_range: r.priceRange,
                        imageUrl: r.imageUrl,
                        neighborhood: r.location.neighborhood,
                        locality: r.location.locality,
                        region: r.location.region,
                        address: r.location.address || null,
                        latitude: r.lat ?? null,
                        longitude: r.lng ?? null,
                    }));

                setSearchResults(results);
                setPagination(null); // No pagination for trending/top-rated
                setCurrentPage(1);

                // Fit map bounds to show all results
                if (results.length > 0 && mapRef.current) {
                    const validResults = results.filter(r => r.latitude != null && r.longitude != null);
                    if (validResults.length > 0) {
                        const bounds = L.latLngBounds(
                            validResults.map(r => [r.latitude!, r.longitude!] as [number, number])
                        );
                        mapRef.current.fitBounds(bounds, { padding: [50, 50] });
                    }
                }
            } catch (err) {
                console.error(`Error fetching ${mode} restaurants:`, err);
                toast.error(`Failed to fetch ${mode === "trending" ? "trending" : "top-rated"} restaurants`);
                setSearchResults([]);
            } finally {
                setLoading(false);
            }
        }
    }, [auth, cityConfig]);

    const handlePageChange = (page: number) => {
        handleSearch(page);
    };

    return (
        <SidebarProvider
            defaultOpen={true}
            style={
                {
                    "--sidebar-width": "45rem",
                    "--sidebar-width-icon": "420px",
                } as React.CSSProperties
            }
            className="flex-1 min-h-0"
        >
            <SearchSidebar
                filters={filters}
                setFilters={setFilters}
                searchResults={searchResults}
                loading={loading}
                hasSearched={hasSearched}
                pagination={pagination}
                currentPage={currentPage}
                hasNextPage={hasNextPage}
                inputsHaveChanged={inputsHaveChanged}
                onSearch={handleSearch}
                onPageChange={handlePageChange}
                onModeChange={handleModeChange}
                onCardClick={handleCardClick}
                onCardHover={handleCardHover}
            />

            <SidebarInset className="hidden md:flex min-h-0 overflow-hidden">
                {/* Map Container - fills all available space */}
                <div className="relative flex-1 min-h-0 h-full">
                    <Stack
                        itemsAlignX="center"
                        className="absolute top-4 left-1/2 -translate-x-1/2 z-1000"
                    >
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
                    </Stack>

                    <MapView
                        searchResults={searchResults}
                        mapCenter={mapCenter}
                        mapRef={mapRef}
                        markerRefsMap={markerRefsMap}
                    />
                </div>
            </SidebarInset>
        </SidebarProvider>
    );
}
