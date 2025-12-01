/**
 * API client for Resy Bot backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

export interface VenueData {
  name: string;
  venue_id: string;
  type: string;
  address: string;
  neighborhood: string;
  price_range: number;
  rating: number | null;
}

export interface SearchResult {
  id: string;
  name: string;
  locality: string;
  region: string;
  neighborhood: string;
  type: string;
  price_range: number;
  address: string | null;
  imageUrl?: string | null;
}

export interface ReservationRequest {
  venueId: string;
  partySize: string;
  date: string;
  hour: string;
  minute: string;
  windowHours: string;
  seatingType?: string;
  dropHour: string;
  dropMinute: string;
}

export interface GroundingChunk {
  index: number;
  title: string;
  uri: string | null;
  snippet: string | null;
}

export interface KeyFact {
  fact: string;
  citationIndices: number[];
}

export interface GroundingSupport {
  segment: {
    startIndex: number | null;
    endIndex: number | null;
    text: string | null;
  };
  groundingChunkIndices: number[];
  confidenceScores: number[];
}

export interface GeminiSearchResponse {
  summary: string;
  keyFacts: KeyFact[];
  webSearchQueries: string[];
  groundingChunks: GroundingChunk[];
  groundingSupports: GroundingSupport[];
  rawGroundingMetadata: {
    retrievalQueries: string[];
    searchEntryPoint: string | null;
  };
  suggestedFollowUps: string[];
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

/**
 * Search for restaurants by name
 */
export async function searchRestaurants(query: string): Promise<SearchResult[]> {
  const response = await fetch(`${API_BASE_URL}/api/search?query=${encodeURIComponent(query)}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to search restaurants');
  }

  const result: ApiResponse<SearchResult[]> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to search restaurants');
  }

  return result.data;
}

/**
 * Search for restaurant by venue ID
 */
export async function searchRestaurant(venueId: string): Promise<VenueData> {
  const response = await fetch(`${API_BASE_URL}/api/venue/${venueId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch restaurant');
  }

  const result: ApiResponse<VenueData> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch restaurant');
  }

  return result.data;
}

/**
 * Make a reservation
 */
export async function makeReservation(
  request: ReservationRequest
): Promise<{ resy_token: string }> {
  const response = await fetch(`${API_BASE_URL}/api/reservation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to make reservation');
  }

  const result: ApiResponse<{ resy_token: string }> = await response.json();

  if (!result.success) {
    throw new Error(result.error || 'Failed to make reservation');
  }

  return { resy_token: result.message || 'Reservation successful' };
}

/**
 * Get AI-powered reservation information using Gemini
 */
export async function getGeminiSearch(restaurantName: string, venueId?: string): Promise<GeminiSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/gemini-search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ restaurantName, venueId }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get AI summary');
  }

  const result: ApiResponse<GeminiSearchResponse> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to get AI summary');
  }

  return result.data;
}

export interface CalendarAvailability {
  date: string;
  available: boolean;
  soldOut: boolean;
  closed: boolean;
}

export interface CalendarData {
  availability: CalendarAvailability[];
  startDate: string;
  endDate: string;
}

/**
 * Get restaurant availability calendar
 */
export async function getCalendar(venueId: string, partySize?: string): Promise<CalendarData> {
  const params = new URLSearchParams();
  if (partySize) {
    params.append('partySize', partySize);
  }

  const url = `${API_BASE_URL}/api/calendar/${venueId}${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch calendar');
  }

  const result: ApiResponse<CalendarData> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch calendar');
  }

  return result.data;
}

export interface VenuePhotoData {
  photoUrl: string;  // For backwards compatibility
  photoUrls: string[];  // Array of photo URLs
  placeName: string;
  placeAddress: string;
}

/**
 * Get restaurant photo URL from Google Places
 */
export async function getVenuePhoto(venueId: string, restaurantName: string): Promise<VenuePhotoData> {
  const params = new URLSearchParams();
  params.append('name', restaurantName);

  const url = `${API_BASE_URL}/api/venue/${venueId}/photo?${params.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch venue photo');
  }

  const result: ApiResponse<VenuePhotoData> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch venue photo');
  }

  return result.data;
}

/**
 * Check server health
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    const data = await response.json();
    return data.status === 'ok';
  } catch {
    return false;
  }
}

export interface TrendingRestaurant {
  id: string;
  name: string;
  type: string;
  priceRange: number;
  location: {
    neighborhood: string;
    locality: string;
    region: string;
    address: string;
  };
  imageUrl: string | null;
  rating: number | null;
}

/**
 * Get trending/climbing restaurants
 */
export async function getTrendingRestaurants(limit?: number): Promise<TrendingRestaurant[]> {
  const params = new URLSearchParams();
  if (limit) {
    params.append('limit', limit.toString());
  }

  const url = `${API_BASE_URL}/api/climbing${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch trending restaurants');
  }

  const result: ApiResponse<TrendingRestaurant[]> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch trending restaurants');
  }

  return result.data;
}

/**
 * Get top-rated restaurants
 */
export async function getTopRatedRestaurants(limit?: number): Promise<TrendingRestaurant[]> {
  const params = new URLSearchParams();
  if (limit) {
    params.append('limit', limit.toString());
  }

  const url = `${API_BASE_URL}/api/top-rated${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch top-rated restaurants');
  }

  const result: ApiResponse<TrendingRestaurant[]> = await response.json();

  if (!result.success || !result.data) {
    throw new Error(result.error || 'Failed to fetch top-rated restaurants');
  }

  return result.data;
}

export interface VenueLinks {
  googleMaps: string | null;
  resy: string | null;
}

export interface VenueBasicData {
  name: string;
  type: string;
  address: string;
  neighborhood: string;
  priceRange: number;
  rating: number;
}

export interface VenueLinksResponse {
  links: VenueLinks;
  venueData: VenueBasicData;
}

/**
 * Get social media links and basic data for a venue (Google Maps, Resy, Beli)
 */
export async function getVenueLinks(venueId: string): Promise<VenueLinksResponse> {
  console.log(`[API] Fetching venue links for venue_id: ${venueId}`);
  const startTime = performance.now();

  try {
    const response = await fetch(`${API_BASE_URL}/api/venue-links/${venueId}`);

    if (!response.ok) {
      console.error(`[API] Failed to fetch venue links. Status: ${response.status}`);
      throw new Error('Failed to fetch venue links');
    }

    const result = await response.json();

    if (!result.success) {
      console.error(`[API] API returned error:`, result.error);
      throw new Error(result.error || 'Failed to fetch venue links');
    }

    const elapsedTime = (performance.now() - startTime).toFixed(0);
    const foundCount = Object.values(result.links).filter(link => link !== null).length;
    console.log(`[API] ✓ Successfully fetched venue links in ${elapsedTime}ms. Found ${foundCount}/3 links:`, result.links);

    return {
      links: result.links,
      venueData: result.venueData
    };
  } catch (error) {
    const elapsedTime = (performance.now() - startTime).toFixed(0);
    console.error(`[API] ✗ Error fetching venue links after ${elapsedTime}ms:`, error);
    throw error;
  }
}
