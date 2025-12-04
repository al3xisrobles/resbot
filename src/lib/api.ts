/**
 * API client for Resy Bot backend
 * Now using Cloud Functions instead of Flask server
 */

// Cloud Function URLs
const CLOUD_FUNCTIONS_BASE =
  "https://us-central1-resybot-bd2db.cloudfunctions.net";

const API_ENDPOINTS = {
  search: `${CLOUD_FUNCTIONS_BASE}/search`,
  search_map: `${CLOUD_FUNCTIONS_BASE}/search_map`,
  venue: `${CLOUD_FUNCTIONS_BASE}/venue`,
  venue_links: `${CLOUD_FUNCTIONS_BASE}/venue_links`,
  venue_photo: `${CLOUD_FUNCTIONS_BASE}/venue_photo`,
  venue_photo_proxy: `${CLOUD_FUNCTIONS_BASE}/venue_photo_proxy`,
  calendar: `${CLOUD_FUNCTIONS_BASE}/calendar`,
  reservation: `${CLOUD_FUNCTIONS_BASE}/reservation`,
  gemini_search: `${CLOUD_FUNCTIONS_BASE}/gemini_search`,
  climbing: `${CLOUD_FUNCTIONS_BASE}/climbing`,
  top_rated: `${CLOUD_FUNCTIONS_BASE}/top_rated`,
  health: "https://health-hypomglm7a-uc.a.run.app",
};

import type {
  SearchFilters,
  SearchResponse,
  VenueData,
  ReservationRequest,
  GeminiSearchResponse,
  CalendarData,
  VenuePhotoData,
  TrendingRestaurant,
  VenueLinksResponse,
  MapSearchFilters,
  ApiResponse,
} from "./interfaces";

/**
 * Search for restaurants by name and/or filters
 */
export async function searchRestaurants(
  filters: SearchFilters
): Promise<SearchResponse> {
  const params = new URLSearchParams();

  if (filters.query) {
    params.append("query", filters.query);
  }

  if (filters.cuisines && filters.cuisines.length > 0) {
    params.append("cuisines", filters.cuisines.join(","));
  }

  if (filters.neighborhoods && filters.neighborhoods.length > 0) {
    params.append("neighborhoods", filters.neighborhoods.join(","));
  }

  if (filters.priceRanges && filters.priceRanges.length > 0) {
    params.append("priceRanges", filters.priceRanges.join(","));
  }

  if (filters.offset !== undefined) {
    params.append("offset", filters.offset.toString());
  }

  if (filters.perPage) {
    params.append("perPage", filters.perPage.toString());
  }

  // Always send day and party size if provided (for availability fetching)
  if (filters.day) {
    params.append("available_day", filters.day);
  }

  if (filters.partySize) {
    params.append("available_party_size", filters.partySize);
  }

  if (filters.availableOnly) {
    if (!filters.day || !filters.partySize) {
      throw new Error(
        "Both day and party_size must be provided when available_only is true"
      );
    }
    params.append("available_only", "true");
  }

  const response = await fetch(`${API_ENDPOINTS.search}?${params.toString()}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to search restaurants");
  }

  const result: any = await response.json();

  console.log("[API] searchRestaurants raw response:", {
    hasPagination: !!result.pagination,
    pagination: result.pagination,
    paginationKeys: result.pagination ? Object.keys(result.pagination) : [],
  });

  if (!result.success) {
    throw new Error(result.error || "Failed to search restaurants");
  }

  return {
    results: result.data || [],
    pagination: result.pagination || {
      offset: 0,
      perPage: 20,
      nextOffset: null,
      hasMore: false,
    },
  };
}

/**
 * Search for restaurants by name and/or filters with map bounds
 */
export async function searchRestaurantsByMap(
  filters: MapSearchFilters
): Promise<SearchResponse> {
  const params = new URLSearchParams();

  params.append("swLat", filters.swLat.toString());
  params.append("swLng", filters.swLng.toString());
  params.append("neLat", filters.neLat.toString());
  params.append("neLng", filters.neLng.toString());

  if (filters.query) {
    params.append("query", filters.query);
  }

  if (filters.cuisines && filters.cuisines.length > 0) {
    params.append("cuisines", filters.cuisines.join(","));
  }

  if (filters.priceRanges && filters.priceRanges.length > 0) {
    params.append("priceRanges", filters.priceRanges.join(","));
  }

  if (filters.offset !== undefined) {
    params.append("offset", filters.offset.toString());
  }

  if (filters.perPage) {
    params.append("perPage", filters.perPage.toString());
  }

  // Always send day and party size if provided (for availability fetching)
  if (filters.day) {
    params.append("available_day", filters.day);
  }

  if (filters.partySize) {
    params.append("available_party_size", filters.partySize);
  }

  if (filters.desiredTime) {
    params.append("desired_time", filters.desiredTime);
  }

  if (filters.availableOnly) {
    if (!filters.day || !filters.partySize) {
      throw new Error(
        "Both day and party_size must be provided when available_only is true"
      );
    }
    params.append("available_only", "true");
  }

  if (filters.notReleasedOnly) {
    if (!filters.day || !filters.partySize) {
      throw new Error(
        "Both day and party_size must be provided when not_released_only is true"
      );
    }
    params.append("not_released_only", "true");
  }

  const response = await fetch(
    `${API_ENDPOINTS.search_map}?${params.toString()}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to search restaurants by map");
  }

  const result: any = await response.json();

  console.log("[API] searchRestaurantsByMap raw response:", {
    hasPagination: !!result.pagination,
    pagination: result.pagination,
    paginationKeys: result.pagination ? Object.keys(result.pagination) : [],
  });

  if (!result.success) {
    throw new Error(result.error || "Failed to search restaurants by map");
  }

  return {
    results: result.data || [],
    pagination: result.pagination || {
      offset: 0,
      perPage: 20,
      nextOffset: null,
      hasMore: false,
    },
  };
}

/**
 * Search for restaurant by venue ID
 */
export async function searchRestaurant(venueId: string): Promise<VenueData> {
  const response = await fetch(`${API_ENDPOINTS.venue}?id=${venueId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to fetch restaurant");
  }

  const result: ApiResponse<VenueData> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch restaurant");
  }

  return result.data;
}

/**
 * Make a reservation
 */
export async function makeReservation(
  request: ReservationRequest
): Promise<{ resy_token: string }> {
  const response = await fetch(API_ENDPOINTS.reservation, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to make reservation");
  }

  const result: ApiResponse<{ resy_token: string }> = await response.json();

  if (!result.success) {
    throw new Error(result.error || "Failed to make reservation");
  }

  return { resy_token: result.message || "Reservation successful" };
}

/**
 * Get AI-powered reservation information using Gemini
 */
export async function getGeminiSearch(
  restaurantName: string,
  venueId?: string
): Promise<GeminiSearchResponse> {
  const response = await fetch(API_ENDPOINTS.gemini_search, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ restaurantName, venueId }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to get AI summary");
  }

  const result: ApiResponse<GeminiSearchResponse> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to get AI summary");
  }

  return result.data;
}

/**
 * Get restaurant availability calendar
 */
export async function getCalendar(
  venueId: string,
  partySize?: string
): Promise<CalendarData> {
  const params = new URLSearchParams();
  params.append("id", venueId);
  if (partySize) {
    params.append("partySize", partySize);
  }

  const url = `${API_ENDPOINTS.calendar}?${params.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to fetch calendar");
  }

  const result: ApiResponse<CalendarData> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch calendar");
  }

  return result.data;
}

/**
 * Get restaurant photo URL from Google Places
 */
export async function getVenuePhoto(
  venueId: string,
  restaurantName: string
): Promise<VenuePhotoData | null> {
  const params = new URLSearchParams();
  params.append("id", venueId);
  params.append("name", restaurantName);

  const url = `${API_ENDPOINTS.venue_photo}?${params.toString()}`;

  try {
    const response = await fetch(url);

    // Handle 404 gracefully - restaurant just doesn't have a photo
    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      console.warn(
        `Failed to fetch venue photo for ${restaurantName}:`,
        error.error || response.statusText
      );
      return null;
    }

    const result: ApiResponse<VenuePhotoData> = await response.json();

    if (!result.success || !result.data) {
      console.warn(`No photo data for ${restaurantName}:`, result.error);
      return null;
    }

    return result.data;
  } catch (error) {
    console.warn(`Error fetching venue photo for ${restaurantName}:`, error);
    return null;
  }
}

/**
 * Check server health
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(API_ENDPOINTS.health);
    const data = await response.json();
    return data.status === "ok";
  } catch {
    return false;
  }
}

/**
 * Get trending/climbing restaurants
 */
export async function getTrendingRestaurants(
  limit?: number
): Promise<TrendingRestaurant[]> {
  const params = new URLSearchParams();
  if (limit) {
    params.append("limit", limit.toString());
  }

  const url = `${API_ENDPOINTS.climbing}${
    params.toString() ? "?" + params.toString() : ""
  }`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to fetch trending restaurants");
  }

  const result: ApiResponse<TrendingRestaurant[]> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch trending restaurants");
  }

  return result.data;
}

/**
 * Get top-rated restaurants
 */
export async function getTopRatedRestaurants(
  limit?: number
): Promise<TrendingRestaurant[]> {
  const params = new URLSearchParams();
  if (limit) {
    params.append("limit", limit.toString());
  }

  const url = `${API_ENDPOINTS.top_rated}${
    params.toString() ? "?" + params.toString() : ""
  }`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to fetch top-rated restaurants");
  }

  const result: ApiResponse<TrendingRestaurant[]> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch top-rated restaurants");
  }

  return result.data;
}

/**
 * Get social media links and basic data for a venue (Google Maps, Resy, Beli)
 */
export async function getVenueLinks(
  venueId: string
): Promise<VenueLinksResponse> {
  console.log(`[API] Fetching venue links for venue_id: ${venueId}`);
  const startTime = performance.now();

  try {
    const response = await fetch(`${API_ENDPOINTS.venue_links}?id=${venueId}`);

    if (!response.ok) {
      console.error(
        `[API] Failed to fetch venue links. Status: ${response.status}`
      );
      throw new Error("Failed to fetch venue links");
    }

    const result = await response.json();

    if (!result.success) {
      console.error(`[API] API returned error:`, result.error);
      throw new Error(result.error || "Failed to fetch venue links");
    }

    const elapsedTime = (performance.now() - startTime).toFixed(0);
    const foundCount = Object.values(result.links).filter(
      (link) => link !== null
    ).length;
    console.log(
      `[API] ✓ Successfully fetched venue links in ${elapsedTime}ms. Found ${foundCount}/3 links:`,
      result.links
    );

    return {
      links: result.links,
      venueData: result.venueData,
    };
  } catch (error) {
    const elapsedTime = (performance.now() - startTime).toFixed(0);
    console.error(
      `[API] ✗ Error fetching venue links after ${elapsedTime}ms:`,
      error
    );
    throw error;
  }
}
