/**
 * Application Types
 * These interfaces represent the domain models and data structures used throughout the app
 */

/**
 * Venue data model
 */
export interface VenueData {
  name: string;
  venue_id: string;
  type: string;
  address: string;
  neighborhood: string;
  price_range: number;
  rating: number | null;
  photoUrls: string[]; // List of photo URLs from Resy API
  description?: string; // Description from metadata
  requiresPaymentMethod?: boolean | null; // true = required, false = not required, null = unknown */
}

/**
 * Search result model for individual restaurants
 */
export interface SearchResult {
  id: string;
  name: string;
  locality: string;
  region: string;
  neighborhood: string;
  type: string;
  price_range: number;
  address: string | null;
  latitude?: number | null;
  longitude?: number | null;
  imageUrl?: string | null;
  availableTimes?: string[]; // Available reservation time slots
  availabilityStatus?: string; // Status message when no times available (e.g., "Fully booked", "Closed")
}

/**
 * Reservation request payload
 */
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

/**
 * Gemini AI search response models
 */
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

/**
 * Search filter models
 */
export interface SearchFilters {
  query?: string;
  cuisines?: string[];
  neighborhoods?: string[];
  priceRanges?: string[];
  offset?: number;
  perPage?: number;
  availableOnly?: boolean;
  notReleasedOnly?: boolean;
  day?: string; // Required if available_only or notReleasedOnly is true
  partySize?: string; // Required if available_only or notReleasedOnly is true
}

export interface MapSearchFilters {
  swLat: number;
  swLng: number;
  neLat: number;
  neLng: number;
  query?: string;
  cuisines?: string[];
  priceRanges?: string[];
  offset?: number;
  perPage?: number;
  availableOnly?: boolean;
  notReleasedOnly?: boolean;
  day?: string; // Required if available_only or notReleasedOnly is true
  partySize?: string; // Required if available_only or notReleasedOnly is true
  desiredTime?: string; // Desired time in HH:MM format for sorting available times
  jobId?: string; // Optional job ID for tracking asynchronous searches
}

/**
 * Pagination model
 */
export interface SearchPagination {
  offset: number;
  perPage: number;
  nextOffset: number | null;
  hasMore: boolean;
  total?: number; // Total from Resy API (unfiltered estimate) - only for non-filtered results
  // For availability-filtered results (available_only or not_released_only):
  isFiltered?: boolean; // True when results are filtered by availability
  foundSoFar?: number; // Number of matching results found so far (progressive count)
}

/**
 * Search response model (used internally by api.ts)
 * This is what api.ts functions return, not what the API returns
 */
export interface SearchResponse {
  results: SearchResult[];
  pagination: SearchPagination;
}

/**
 * Calendar availability models
 */
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
 * Venue links models
 */
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
 * Trending restaurant model
 */
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
  lat?: number | null;
  lng?: number | null;
}

export interface Reservation {
  id: string;
  venueId: string;
  venueName: string;
  venueImage: string;
  date: string;
  time: string;
  partySize: number;
  status: "Scheduled" | "Succeeded" | "Failed";
  attemptedAt?: number;
  note?: string;
  snipeTime?: string; // ISO timestamp when snipe runs
  aiSummary?: string; // AI-generated summary of what happened
  dropDate?: string; // "YYYY-MM-DD" - drop date (for editing)
  windowHours?: number; // Window hours (for editing)
  seatingType?: string; // Seating type (for editing)
  dropHour?: number; // Drop hour (for editing)
  dropMinute?: number; // Drop minute (for editing)
}
