/**
 * API client for Resy Bot backend
 * Now using Cloud Functions instead of Flask server
 * Uses centralized apiClient for trace header propagation
 * Types from generated schemas (single source of truth with backend)
 */
import { apiGet, apiPost, apiDelete, API_ENDPOINTS } from "./apiClient";
import type {
  SearchApiResponse,
  VenueLinksApiResponse,
  OnboardingApiResponse,
  MeResponse,
  GeminiSearchApiResponse,
} from "./api-schema-registry";

import type {
  SearchFilters,
  SearchResponse,
  VenueData,
  CalendarData,
  TrendingRestaurant,
  VenueLinksResponse,
  MapSearchFilters,
  ApiResponse,
  GeminiSearchResponse,
  SearchResult,
  SearchPagination,
} from "./interfaces";

/**
 * Search for restaurants by name and/or filters
 */
export async function searchRestaurants(
  userId: string,
  filters: SearchFilters,
  cityId?: string
): Promise<SearchResponse> {
  // Get city from parameter or localStorage (for backward compatibility)
  const city = cityId || (typeof window !== "undefined" ? localStorage.getItem("resbot_selected_city") || "nyc" : "nyc");

  const params: Record<string, string | number> = {
    userId,
    city,
  };

  if (filters.query) {
    params.query = filters.query;
  }

  if (filters.cuisines && filters.cuisines.length > 0) {
    params.cuisines = filters.cuisines.join(",");
  }

  if (filters.neighborhoods && filters.neighborhoods.length > 0) {
    params.neighborhoods = filters.neighborhoods.join(",");
  }

  if (filters.priceRanges && filters.priceRanges.length > 0) {
    params.priceRanges = filters.priceRanges.join(",");
  }

  if (filters.offset !== undefined) {
    params.offset = filters.offset;
  }

  if (filters.perPage) {
    params.perPage = filters.perPage;
  }

  // Only send day and party size if availability filters are enabled
  // This prevents unnecessary availability fetching when filters aren't active
  if (filters.availableOnly || filters.notReleasedOnly) {
    if (filters.day) {
      params.available_day = filters.day;
    }

    if (filters.partySize) {
      params.available_party_size = filters.partySize;
    }
  }

  if (filters.availableOnly) {
    if (!filters.day || !filters.partySize) {
      throw new Error(
        "Both day and party_size must be provided when available_only is true"
      );
    }
    params.available_only = "true";
  }

  const result = await apiGet<SearchApiResponse>(API_ENDPOINTS.search, params);

  console.log("[API] searchRestaurants raw response:", {
    hasPagination: !!result.pagination,
    pagination: result.pagination,
    paginationKeys: result.pagination ? Object.keys(result.pagination) : [],
  });

  if (!result.success) {
    throw new Error(result.error || "Failed to search restaurants");
  }

  return {
    results: (result.data?.results || []) as SearchResult[],
    pagination: (result.data?.pagination || {
      offset: 0,
      perPage: 20,
      nextOffset: null,
      hasMore: false,
    }) as SearchPagination,
  };
}

/**
 * Search for restaurants by name and/or filters with map bounds
 */
export async function searchRestaurantsByMap(
  userId: string,
  filters: MapSearchFilters,
  signal?: AbortSignal
): Promise<SearchResponse> {
  const params: Record<string, string | number> = {
    userId,
    swLat: filters.swLat,
    swLng: filters.swLng,
    neLat: filters.neLat,
    neLng: filters.neLng,
  };

  if (filters.jobId) {
    params.jobId = filters.jobId;
  }

  if (filters.query) {
    params.query = filters.query;
  }

  if (filters.cuisines && filters.cuisines.length > 0) {
    params.cuisines = filters.cuisines.join(",");
  }

  if (filters.priceRanges && filters.priceRanges.length > 0) {
    params.priceRanges = filters.priceRanges.join(",");
  }

  if (filters.offset !== undefined) {
    params.offset = filters.offset;
  }

  if (filters.perPage) {
    params.perPage = filters.perPage;
  }

  // Only send day, party size, and desired time if availability filters are enabled
  // This prevents unnecessary availability fetching when filters aren't active
  if (filters.availableOnly || filters.notReleasedOnly) {
    if (filters.day) {
      params.available_day = filters.day;
    }

    if (filters.partySize) {
      params.available_party_size = filters.partySize;
    }

    if (filters.desiredTime) {
      params.desired_time = filters.desiredTime;
    }
  }

  if (filters.availableOnly) {
    if (!filters.day || !filters.partySize) {
      throw new Error(
        "Both day and party_size must be provided when available_only is true"
      );
    }
    params.available_only = "true";
  }

  if (filters.notReleasedOnly) {
    if (!filters.day || !filters.partySize) {
      throw new Error(
        "Both day and party_size must be provided when not_released_only is true"
      );
    }
    params.not_released_only = "true";
  }

  const result = await apiGet<SearchApiResponse>(API_ENDPOINTS.searchMap, params, signal);

  console.log("[API] searchRestaurantsByMap raw response:", {
    hasPagination: !!result.pagination,
    pagination: result.pagination,
    paginationKeys: result.pagination ? Object.keys(result.pagination) : [],
  });

  if (!result.success) {
    throw new Error(result.error || "Failed to search restaurants by map");
  }

  return {
    results: (result.data?.results || []) as SearchResult[],
    pagination: (result.data?.pagination || {
      offset: 0,
      perPage: 20,
      nextOffset: null,
      hasMore: false,
    }) as SearchPagination,
  };
}

/**
 * Search for restaurant by venue ID
 */
export async function searchRestaurant(
  userId: string,
  venueId: string
): Promise<VenueData> {
  const result = await apiGet<ApiResponse<VenueData>>(API_ENDPOINTS.venue, {
    id: venueId,
    userId,
  });

  console.log("[API] searchRestaurant raw response:", result);

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch restaurant");
  }

  return result.data;
}

/**
 * Get AI-powered reservation information using Gemini
 */
export async function getGeminiSearch(
  userId: string,
  restaurantName: string,
  venueId?: string,
  cityId?: string
): Promise<GeminiSearchResponse> {
  // Get city from parameter or localStorage (for backward compatibility)
  const city = cityId || (typeof window !== "undefined" ? localStorage.getItem("resbot_selected_city") || "nyc" : "nyc");

  const body: Record<string, string> = { restaurantName, city };
  if (venueId) body.venueId = venueId;

  const result = await apiPost<GeminiSearchApiResponse>(
    API_ENDPOINTS.geminiSearch,
    body,
    { userId }
  );

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to get AI summary");
  }

  return result.data as unknown as GeminiSearchResponse;
}

/**
 * Get AI-powered summary of reservation attempt logs using Gemini
 */
export async function getSnipeLogsSummary(
  jobId: string
): Promise<string> {
  const result = await apiPost<ApiResponse<{ summary: string }>>(
    API_ENDPOINTS.summarizeSnipeLogs,
    { jobId }
  );

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to get log summary. Results looks like this: " + JSON.stringify(result));
  }

  return result.data.summary;
}

/**
 * Get restaurant availability calendar
 */
export async function getCalendar(
  userId: string,
  venueId: string,
  partySize?: string
): Promise<CalendarData> {
  const params: Record<string, string> = {
    id: venueId,
    userId,
  };
  if (partySize) {
    params.partySize = partySize;
  }

  const result = await apiGet<ApiResponse<CalendarData>>(API_ENDPOINTS.calendar, params);

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch calendar. Results looks like this: " + JSON.stringify(result));
  }

  return result.data;
}

/**
 * Get available time slots for a specific venue and date
 */
export async function getSlots(
  userId: string,
  venueId: string,
  date: string,
  partySize?: string
): Promise<{ times: string[]; status: string | null }> {
  const params: Record<string, string> = {
    venueId,
    date,
    userId,
  };
  if (partySize) {
    params.partySize = partySize;
  }

  console.log("[getSlots] Making request:", {
    venueId,
    date,
    partySize,
    userId,
  });

  try {
    const result = await apiGet<ApiResponse<{ times: string[]; status: string | null }>>(
      API_ENDPOINTS.slots,
      params
    );

    if (!result.success || !result.data) {
      console.error("[getSlots] Result not successful:", result);
      throw new Error(result.error || "Failed to fetch slots");
    }

    console.log("[getSlots] Success:", result.data);
    return result.data;
  } catch (err) {
    console.error("[getSlots] Exception caught:", {
      error: err,
      errorMessage: err instanceof Error ? err.message : String(err),
      errorStack: err instanceof Error ? err.stack : undefined,
      errorName: err instanceof Error ? err.name : typeof err,
      venueId,
      date,
      partySize,
      userId,
    });
    throw err;
  }
}

/**
 * Check server health
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const data = await apiGet<{ status: string }>(API_ENDPOINTS.health);
    return data.status === "ok";
  } catch {
    return false;
  }
}

/**
 * Get trending/climbing restaurants
 */
export async function getTrendingRestaurants(
  userId?: string | null,
  limit?: number,
  city?: string
): Promise<TrendingRestaurant[]> {
  const params: Record<string, string | number> = {};
  if (userId) {
    params.userId = userId;
  }
  if (limit) {
    params.limit = limit;
  }
  if (city) {
    params.city = city;
  }

  const result = await apiGet<ApiResponse<TrendingRestaurant[]>>(
    API_ENDPOINTS.climbing,
    params
  );

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch trending restaurants");
  }

  return result.data;
}

/**
 * Get top-rated restaurants
 */
export async function getTopRatedRestaurants(
  userId?: string | null,
  limit?: number,
  city?: string
): Promise<TrendingRestaurant[]> {
  const params: Record<string, string | number> = {};
  if (userId) {
    params.userId = userId;
  }
  if (limit) {
    params.limit = limit;
  }
  if (city) {
    params.city = city;
  }

  const result = await apiGet<ApiResponse<TrendingRestaurant[]>>(
    API_ENDPOINTS.topRated,
    params
  );

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to fetch top-rated restaurants");
  }

  return result.data;
}

/**
 * Get social media links and basic data for a venue (Google Maps, Resy, Beli)
 */
export async function getVenueLinks(
  userId: string,
  venueId: string
): Promise<VenueLinksResponse> {
  console.log(`[API] Fetching venue links for venue_id: ${venueId}`);
  const startTime = performance.now();

  try {
    const result = await apiGet<VenueLinksApiResponse>(
      API_ENDPOINTS.venueLinks,
      { id: venueId, userId }
    );

    if (!result.success || !result.data) {
      console.error(`[API] API returned error:`, result.error);
      throw new Error(result.error || "Failed to fetch venue links");
    }

    const elapsedTime = (performance.now() - startTime).toFixed(0);
    const foundCount = Object.values(result.data.links).filter(
      (link) => link !== null
    ).length;
    console.log(
      `[API] ✓ Successfully fetched venue links in ${elapsedTime}ms. Found ${foundCount}/2 links:`,
      result.data.links
    );

    return {
      links: result.data.links as VenueLinksResponse["links"],
      venueData: result.data.venueData,
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

/**
 * Connect Resy account via direct API authentication
 */
export async function connectResyAccount(
  userId: string,
  email: string,
  password: string
): Promise<{
  success: boolean;
  hasPaymentMethod?: boolean;
  paymentMethodId?: number;
  error?: string;
}> {
  try {
    const result = await apiPost<OnboardingApiResponse>(
      API_ENDPOINTS.startResyOnboarding,
      { email, password, userId }
    );
    if (!result.success) {
      return { success: false, error: result.error };
    }
    return {
      success: result.success,
      hasPaymentMethod: result.data?.hasPaymentMethod ?? undefined,
      paymentMethodId: result.data?.paymentMethodId ?? undefined,
    };
  } catch (error) {
    console.error("[API] Error connecting Resy account:", error);
    throw error;
  }
}

/**
 * Get user session data including onboarding status
 */
export async function getMe(userId: string): Promise<{
  success: boolean;
  onboardingStatus: 'not_started' | 'completed';
  hasPaymentMethod: boolean;
  resy: {
    email: string;
    firstName: string;
    lastName: string;
    paymentMethodId: number | null;
  } | null;
  error?: string;
}> {
  try {
    const result = await apiGet<MeResponse>(API_ENDPOINTS.me, { userId });
    
    // Extract data from the nested response structure
    if (!result.success || !result.data) {
      throw new Error(result.error || "Failed to get user session data");
    }
    
    return {
      success: result.success,
      onboardingStatus: result.data.onboardingStatus as 'not_started' | 'completed',
      hasPaymentMethod: result.data.hasPaymentMethod,
      resy: result.data.resy,
    };
  } catch (error) {
    console.error("[API] Error getting user session data:", error);
    throw error;
  }
}

/**
 * Check if user has connected their Resy account
 */
export async function checkResyAccountStatus(userId: string): Promise<{
  success: boolean;
  connected: boolean;
  hasPaymentMethod?: boolean;
  email?: string;
  name?: string;
}> {
  try {
    const result = await apiGet<{
      success: boolean;
      connected: boolean;
      hasPaymentMethod?: boolean;
      email?: string;
      name?: string;
    }>(API_ENDPOINTS.resyAccount, { userId });
    return result;
  } catch (error) {
    console.error("[API] Error checking Resy account status:", error);
    throw error;
  }
}

/**
 * Disconnect Resy account
 */
export async function disconnectResyAccount(userId: string): Promise<{
  success: boolean;
  message?: string;
}> {
  try {
    const result = await apiDelete<{
      success: boolean;
      message?: string;
    }>(API_ENDPOINTS.resyAccount, { userId });
    return result;
  } catch (error) {
    console.error("[API] Error disconnecting Resy account:", error);
    throw error;
  }
}

/**
 * Get full Resy credentials including payment methods
 */
export async function getResyCredentials(userId: string): Promise<{
  success: boolean;
  connected: boolean;
  hasPaymentMethod?: boolean;
  paymentMethodId?: number;
  paymentMethods?: Array<{ id: number;[key: string]: unknown }>;
  email?: string;
  firstName?: string;
  lastName?: string;
  name?: string;
  mobileNumber?: string;
  userId?: number;
}> {
  try {
    const result = await apiGet<{
      success: boolean;
      connected: boolean;
      hasPaymentMethod?: boolean;
      paymentMethodId?: number;
      paymentMethods?: Array<{ id: number;[key: string]: unknown }>;
      email?: string;
      firstName?: string;
      lastName?: string;
      name?: string;
      mobileNumber?: string;
      userId?: number;
    }>(API_ENDPOINTS.resyAccount, { userId });
    return result;
  } catch (error) {
    console.error("[API] Error getting Resy credentials:", error);
    throw error;
  }
}

/**
 * Update selected payment method for Resy account
 */
export async function updateResyPaymentMethod(
  userId: string,
  paymentMethodId: number
): Promise<{
  success: boolean;
  message?: string;
  paymentMethodId?: number;
}> {
  try {
    const result = await apiPost<{
      success: boolean;
      message?: string;
      paymentMethodId?: number;
    }>(
      API_ENDPOINTS.resyAccount,
      { paymentMethodId },
      { userId }
    );
    return result;
  } catch (error) {
    console.error("[API] Error updating payment method:", error);
    throw error;
  }
}

/**
 * Update a reservation job
 */
export async function updateReservationJob(
  _userId: string,
  jobId: string,
  updates: {
    date?: string;
    hour?: number;
    minute?: number;
    partySize?: number;
    windowHours?: number;
    seatingType?: string;
    dropDate?: string;
    dropHour?: number;
    dropMinute?: number;
  }
): Promise<{
  success: boolean;
  jobId?: string;
  targetTimeIso?: string;
  error?: string;
}> {
  try {
    const result = await apiPost<{
      success: boolean;
      jobId?: string;
      targetTimeIso?: string;
      error?: string;
    }>(
      API_ENDPOINTS.updateSnipe,
      { jobId, ...updates }
    );
    return result;
  } catch (error) {
    console.error("[API] Error updating reservation job:", error);
    throw error;
  }
}

/**
 * Cancel a reservation job
 */
export async function cancelReservationJob(
  _userId: string,
  jobId: string
): Promise<{
  success: boolean;
  jobId?: string;
  error?: string;
}> {
  try {
    const result = await apiPost<{
      success: boolean;
      jobId?: string;
      error?: string;
    }>(
      API_ENDPOINTS.cancelSnipe,
      { jobId }
    );
    return result;
  } catch (error) {
    console.error("[API] Error canceling reservation job:", error);
    throw error;
  }
}
