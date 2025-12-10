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
import {
  Map,
  MapTileLayer,
  MapMarker,
  MapPopup,
  MapTooltip,
  MapZoomControl,
  MapLocateControl,
} from "@/components/ui/map";
import { Map as LeafletMap, Marker as LeafletMarkerType } from "leaflet";
import * as L from "leaflet";
import { renderToString } from "react-dom/server";
import { Button } from "@/components/ui/button";
import { searchRestaurantsByMap } from "@/lib/api";
import type { SearchPagination, SearchResult } from "@/lib/interfaces";
import { useVenue } from "@/contexts/VenueContext";
import { useAuth } from "@/contexts/AuthContext";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { SearchSidebar, type SearchFilters } from "@/components/SearchSidebar";

// Pre-create icon instances to avoid recreating on every render
const createIcon = (isHovered: boolean) =>
  L.divIcon({
    html: renderToString(
      <MapPin
        className={`size-6 transition-transform duration-300 ease-in-out ${
          isHovered
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

interface MapViewProps {
  searchResults: SearchResult[];
  mapCenter: [number, number];
  mapRef: React.RefObject<LeafletMap | null>;
  markerRefsMap: React.RefObject<Map<string, LeafletMarkerType>>;
}

const MapView = React.memo(function MapView({
  searchResults,
  mapCenter,
  mapRef,
  markerRefsMap,
}: MapViewProps) {
  const venuePositions = useMemo(() => {
    const positions: Record<string, [number, number]> = {};
    searchResults.forEach((result) => {
      if (result.latitude != null && result.longitude != null) {
        positions[result.id] = [result.latitude, result.longitude];
      }
    });
    return positions;
  }, [searchResults]);

  const setMarkerRef = useCallback(
    (id: string, marker: LeafletMarkerType | null) => {
      if (marker) {
        markerRefsMap.current.set(id, marker);
      } else {
        markerRefsMap.current.delete(id);
      }
    },
    [markerRefsMap]
  );

  return (
    <Map center={mapCenter} zoom={13} className="h-full w-full" ref={mapRef}>
      <MapTileLayer />
      {searchResults.map((result) => {
        const position = venuePositions[result.id];

        if (!position) return null;

        return (
          <MapMarker
            key={result.id}
            position={position}
            ref={(marker: LeafletMarkerType | null) =>
              setMarkerRef(result.id, marker)
            }
            icon={<MapPin className="size-6 text-black fill-black" />}
          >
            <MapTooltip side="top">
              <div className="font-medium">{result.name}</div>
              <div className="text-xs text-muted-foreground">
                {result.neighborhood || "Manhattan"}
              </div>
            </MapTooltip>
            <MapPopup>
              <div className="flex flex-col gap-2 items-start">
                <div className="font-semibold text-lg">{result.name}</div>
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
  );
});

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
  const [inputsHaveChanged, setInputsHaveChanged] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("browse");
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

  const mapCenter = useMemo(() => [40.7589, -73.9851] as [number, number], []);

  const handleMapMove = () => {
    setInputsHaveChanged(true);
  };

  useEffect(() => {
    setInputsHaveChanged(true);
    console.log("Filters:", filters);
    pageCache.current = {};
    currentSearchKey.current = "";
  }, [filters, reservationForm, activeTab]);

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

  const handleSearch = async (page: number = 1) => {
    if (!mapRef.current) return;

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

    if (sw.lat === ne.lat && sw.lng === ne.lng) {
      console.log(
        "[MAP SEARCH] Detected identical coordinates (mobile), using default NYC bounds"
      );
      sw = { lat: 40.7, lng: -74.02 } as L.LatLng;
      ne = { lat: 40.8, lng: -73.93 } as L.LatLng;
    }

    const offset = (page - 1) * 20;

    const shouldApplyFilters = activeTab !== "specific";
    const shouldApplyQuery = activeTab === "specific";

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
        reservationForm={reservationForm}
        setReservationForm={setReservationForm}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        searchResults={searchResults}
        loading={loading}
        hasSearched={hasSearched}
        pagination={pagination}
        currentPage={currentPage}
        hasNextPage={hasNextPage}
        inputsHaveChanged={inputsHaveChanged}
        onSearch={handleSearch}
        onPageChange={handlePageChange}
        onCardClick={handleCardClick}
        onCardHover={handleCardHover}
      />

      <SidebarInset className="hidden md:flex min-h-0 overflow-hidden">
        {/* Map Container - fills all available space */}
        <div className="relative flex-1 min-h-0 h-full">
          {activeTab === "browse" && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-1000">
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
          )}

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
