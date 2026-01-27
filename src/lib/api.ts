/**
 * API client for Resy Bot backend
 * Now using Cloud Functions instead of Flask server
 */
import { CLOUD_FUNCTIONS_BASE } from "../services/firebase";
import { triggerSessionExpiredModal } from "../contexts/ResySessionContext.utils";

/**
 * Custom error class for Resy session expiration (419 error)
 */
export class ResySessionExpiredError extends Error {
  constructor(message = "Resy session expired") {
    super(message);
    this.name = "ResySessionExpiredError";
  }
}

/**
 * Check if an API error response indicates a Resy session expiration (419)
 * and trigger the modal if so
 */
async function handleApiResponse(response: Response): Promise<Response> {
  if (!response.ok) {
    // Check for 419 or 500 with "Unauthorized" message (backend wraps 419 as 500)
    if (response.status === 419) {
      triggerSessionExpiredModal();
      throw new ResySessionExpiredError();
    }

    // Try to parse the error response to check for 419-related errors
    try {
      const errorData = await response.clone().json();
      // Backend returns 500 but the error message contains "419" or "Unauthorized"
      if (
        errorData.error?.includes("419") ||
        errorData.error?.includes("Unauthorized") ||
        (response.status === 500 && errorData.error?.includes("API returned status 419"))
      ) {
        triggerSessionExpiredModal();
        throw new ResySessionExpiredError();
      }
    } catch (e) {
      // If it's already a ResySessionExpiredError, re-throw it
      if (e instanceof ResySessionExpiredError) {
        throw e;
      }
      // Otherwise, continue with normal error handling
    }
  }
  return response;
}

const API_ENDPOINTS = {
  search: `${CLOUD_FUNCTIONS_BASE}/search`,
  search_map: `${CLOUD_FUNCTIONS_BASE}/search_map`,
  venue: `${CLOUD_FUNCTIONS_BASE}/venue`,
  venue_links: `${CLOUD_FUNCTIONS_BASE}/venue_links`,
  calendar: `${CLOUD_FUNCTIONS_BASE}/calendar`,
  slots: `${CLOUD_FUNCTIONS_BASE}/slots`,
  reservation: `${CLOUD_FUNCTIONS_BASE}/reservation`,
  gemini_search: `${CLOUD_FUNCTIONS_BASE}/gemini_search`,
  summarize_snipe_logs: `${CLOUD_FUNCTIONS_BASE}/summarize_snipe_logs`,
  climbing: `${CLOUD_FUNCTIONS_BASE}/climbing`,
  top_rated: `${CLOUD_FUNCTIONS_BASE}/top_rated`,
  health: "https://health-hypomglm7a-uc.a.run.app",
};

import type {
  SearchFilters,
  SearchResponse,
  SearchApiResponse,
  VenueData,
  GeminiSearchResponse,
  CalendarData,
  TrendingRestaurant,
  VenueLinksResponse,
  MapSearchFilters,
  ApiResponse,
} from "./interfaces";

/**
 * Search for restaurants by name and/or filters
 */
export async function searchRestaurants(
  userId: string,
  filters: SearchFilters,
  cityId?: string
): Promise<SearchResponse> {
  const params = new URLSearchParams();
  params.append("userId", userId);

  // Get city from parameter or localStorage (for backward compatibility)
  const city = cityId || (typeof window !== "undefined" ? localStorage.getItem("resbot_selected_city") || "nyc" : "nyc");
  params.append("city", city);

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

  // Only send day and party size if availability filters are enabled
  // This prevents unnecessary availability fetching when filters aren't active
  if (filters.availableOnly || filters.notReleasedOnly) {
    if (filters.day) {
      params.append("available_day", filters.day);
    }

    if (filters.partySize) {
      params.append("available_party_size", filters.partySize);
    }
  }

  if (filters.availableOnly) {
    if (!filters.day || !filters.partySize) {
      throw new Error(
        "Both day and party_size must be provided when available_only is true"
      );
    }
    params.append("available_only", "true");
  }

  const rawResponse = await fetch(`${API_ENDPOINTS.search}?${params.toString()}`);
  const response = await handleApiResponse(rawResponse);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to search restaurants");
  }

  const result: SearchApiResponse = await response.json();

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
  userId: string,
  filters: MapSearchFilters
): Promise<SearchResponse> {
  const params = new URLSearchParams();

  params.append("userId", userId);
  params.append("swLat", filters.swLat.toString());
  params.append("swLng", filters.swLng.toString());
  params.append("neLat", filters.neLat.toString());
  params.append("neLng", filters.neLng.toString());

  if (filters.jobId) {
    params.append("jobId", filters.jobId);
  }

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

  // Only send day, party size, and desired time if availability filters are enabled
  // This prevents unnecessary availability fetching when filters aren't active
  if (filters.availableOnly || filters.notReleasedOnly) {
    if (filters.day) {
      params.append("available_day", filters.day);
    }

    if (filters.partySize) {
      params.append("available_party_size", filters.partySize);
    }

    if (filters.desiredTime) {
      params.append("desired_time", filters.desiredTime);
    }
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

  const rawResponse = await fetch(
    `${API_ENDPOINTS.search_map}?${params.toString()}`
  );
  const response = await handleApiResponse(rawResponse);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to search restaurants by map");
  }

  const result: SearchApiResponse = await response.json();

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
export async function searchRestaurant(
  userId: string,
  venueId: string
): Promise<VenueData> {
  const rawResponse = await fetch(
    `${API_ENDPOINTS.venue}?id=${venueId}&userId=${userId}`
  );
  const response = await handleApiResponse(rawResponse);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to fetch restaurant");
  }

  const result: ApiResponse<VenueData> = await response.json();

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
  const rawResponse = await fetch(
    `${API_ENDPOINTS.gemini_search}?userId=${userId}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ restaurantName, venueId, city }),
    }
  );
  const response = await handleApiResponse(rawResponse);

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
 * Get AI-powered summary of reservation attempt logs using Gemini
 */
export async function getSnipeLogsSummary(
  jobId: string
): Promise<string> {
  const rawResponse = await fetch(API_ENDPOINTS.summarize_snipe_logs, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ jobId }),
  });
  const response = await handleApiResponse(rawResponse);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Failed to get log summary");
  }

  const result: ApiResponse<{ summary: string }> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || "Failed to get log summary");
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
  const params = new URLSearchParams();
  params.append("id", venueId);
  params.append("userId", userId);
  if (partySize) {
    params.append("partySize", partySize);
  }
  const url = `${API_ENDPOINTS.calendar}?${params.toString()}`;
  const rawResponse = await fetch(url);
  const response = await handleApiResponse(rawResponse);

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
 * Get available time slots for a specific venue and date
 */
export async function getSlots(
  userId: string,
  venueId: string,
  date: string,
  partySize?: string
): Promise<{ times: string[]; status: string | null }> {
  const params = new URLSearchParams();
  params.append("venueId", venueId);
  params.append("date", date);
  params.append("userId", userId);
  if (partySize) {
    params.append("partySize", partySize);
  }
  const url = `${API_ENDPOINTS.slots}?${params.toString()}`;

  console.log("[getSlots] Making request:", {
    url,
    venueId,
    date,
    partySize,
    userId,
  });

  try {
    const rawResponse = await fetch(url);
    console.log("[getSlots] Raw response:", {
      status: rawResponse.status,
      statusText: rawResponse.statusText,
      ok: rawResponse.ok,
    });

    const response = await handleApiResponse(rawResponse);

    if (!response.ok) {
      const error = await response.json();
      console.error("[getSlots] Response not OK:", {
        status: response.status,
        error,
      });
      throw new Error(error.error || "Failed to fetch slots");
    }

    const result: ApiResponse<{ times: string[]; status: string | null }> =
      await response.json();

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
      url,
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
  userId?: string | null,
  limit?: number,
  city?: string
): Promise<TrendingRestaurant[]> {
  const params = new URLSearchParams();
  if (userId) {
    params.append("userId", userId);
  }
  if (limit) {
    params.append("limit", limit.toString());
  }
  if (city) {
    params.append("city", city);
  }

  const url = `${API_ENDPOINTS.climbing}${params.toString() ? "?" + params.toString() : ""
    }`;
  const rawResponse = await fetch(url);
  const response = await handleApiResponse(rawResponse);

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
  userId?: string | null,
  limit?: number,
  city?: string
): Promise<TrendingRestaurant[]> {
  const params = new URLSearchParams();
  if (userId) {
    params.append("userId", userId);
  }
  if (limit) {
    params.append("limit", limit.toString());
  }
  if (city) {
    params.append("city", city);
  }

  const url = `${API_ENDPOINTS.top_rated}${params.toString() ? "?" + params.toString() : ""
    }`;
  const rawResponse = await fetch(url);
  const response = await handleApiResponse(rawResponse);

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
  userId: string,
  venueId: string
): Promise<VenueLinksResponse> {
  console.log(`[API] Fetching venue links for venue_id: ${venueId}`);
  const startTime = performance.now();

  try {
    const rawResponse = await fetch(
      `${API_ENDPOINTS.venue_links}?id=${venueId}&userId=${userId}`
    );
    const response = await handleApiResponse(rawResponse);

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
      `[API] ✓ Successfully fetched venue links in ${elapsedTime}ms. Found ${foundCount}/2 links:`,
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
  const url = `${CLOUD_FUNCTIONS_BASE}/start_resy_onboarding`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
        userId: userId,
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Failed to connect Resy account");
    }

    return result;
  } catch (error) {
    console.error("[API] Error connecting Resy account:", error);
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
  const url = `${CLOUD_FUNCTIONS_BASE}/resy_account?userId=${userId}`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to check Resy account status");
    }

    return await response.json();
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
  const url = `${CLOUD_FUNCTIONS_BASE}/resy_account?userId=${userId}`;

  try {
    const response = await fetch(url, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to disconnect Resy account");
    }

    return await response.json();
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
  const url = `${CLOUD_FUNCTIONS_BASE}/resy_account?userId=${userId}`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to get Resy credentials");
    }

    return await response.json();
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
  const url = `${CLOUD_FUNCTIONS_BASE}/resy_account?userId=${userId}`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ paymentMethodId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to update payment method");
    }

    return await response.json();
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
  const url = `${CLOUD_FUNCTIONS_BASE}/update_snipe`;

  try {
    const rawResponse = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jobId,
        ...updates,
      }),
    });

    const response = await handleApiResponse(rawResponse);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to update reservation job");
    }

    return await response.json();
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
  const url = `${CLOUD_FUNCTIONS_BASE}/cancel_snipe`;

  try {
    const rawResponse = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ jobId }),
    });

    const response = await handleApiResponse(rawResponse);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to cancel reservation job");
    }

    return await response.json();
  } catch (error) {
    console.error("[API] Error canceling reservation job:", error);
    throw error;
  }
}
