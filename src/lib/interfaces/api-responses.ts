/**
 * API Response Types
 * These interfaces represent the exact structure returned by the Cloud Functions API
 */

import type {
  SearchResult,
  SearchPagination,
  CalendarData,
  GeminiSearchResponse,
  TrendingRestaurant,
  VenueLinksResponse,
} from "./app-types";

/**
 * Generic API response wrapper
 * Used by most endpoints that return a single data object
 */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

/**
 * Search API response structure
 * Used by /search and /search_map endpoints
 * Standardized: data contains results and pagination
 */
export interface SearchApiResponse {
  success: boolean;
  data?: {
    results: SearchResult[];
    pagination: SearchPagination;
  };
  error?: string;
}

// Re-export common response wrappers for convenience
export type VenueLinksApiResponse = ApiResponse<VenueLinksResponse>;
export type CalendarApiResponse = ApiResponse<CalendarData>;
export type GeminiSearchApiResponse = ApiResponse<GeminiSearchResponse>;
export type TrendingRestaurantsApiResponse = ApiResponse<TrendingRestaurant[]>;
