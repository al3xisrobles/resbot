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
  latitude?: number | null;
  longitude?: number | null;
  imageUrl?: string | null;
  availableTimes?: string[]; // Available reservation time slots
  availabilityStatus?: string; // Status message when no times available (e.g., "Fully booked", "Closed")
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

export interface SearchFilters {
  query?: string;
  cuisines?: string[];
  neighborhoods?: string[];
  priceRanges?: string[];
  offset?: number;
  perPage?: number;
  availableOnly?: boolean;
  day?: string; // Required if available_only is true
  partySize?: string; // Required if available_only is true
}

export interface SearchPagination {
  offset: number;
  perPage: number;
  nextOffset: number | null;
  hasMore: boolean;
  total?: number; // Total from Resy API (unfiltered estimate)
}

export interface SearchResponse {
  results: SearchResult[];
  pagination: SearchPagination;
}

export interface VenuePhotoData {
  photoUrl: string; // For backwards compatibility
  photoUrls: string[]; // Array of photo URLs
  placeName: string;
  placeAddress: string;
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
