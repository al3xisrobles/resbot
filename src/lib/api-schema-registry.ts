/**
 * Central registry of API response schemas.
 * Uses generated Zod schemas - single source of truth from backend Pydantic models.
 * Import types from here for type-safe API usage.
 */
import type { components } from "./generated/api.types";
import { schemas } from "./generated/api.schemas";
import type { z } from "zod";

const {
  ApiResponse_MeData,
  ApiResponse_VenueLinksData,
  ApiResponse_SearchData,
  ApiResponse_VenueDetailData,
  ApiResponse_CalendarData,
  ApiResponse_SlotsData,
  ApiResponse_OnboardingData,
  ApiResponse_AccountStatusData,
  ApiResponse_DisconnectData,
  ApiResponse_TrendingRestaurantsData,
  ApiResponse_GeminiSearchData,
  ApiResponse_SummaryData,
  ApiResponse_VenuePaymentRequirementData,
  ApiResponse_JobCreatedData,
  ApiResponse_JobUpdatedData,
  ApiResponse_JobCancelledData,
  ApiResponse_ReservationCreatedData,
  ApiResponse_PaymentMethodUpdateData,
} = schemas;

// Re-export schemas for runtime validation
export const API_SCHEMAS = {
  me: { GET: ApiResponse_MeData },
  venue: { GET: ApiResponse_VenueDetailData },
  venue_links: { GET: ApiResponse_VenueLinksData },
  check_venue_payment_requirement: { GET: ApiResponse_VenuePaymentRequirementData },
  search: { GET: ApiResponse_SearchData },
  search_map: { GET: ApiResponse_SearchData },
  calendar: { GET: ApiResponse_CalendarData },
  slots: { GET: ApiResponse_SlotsData },
  climbing: { GET: ApiResponse_TrendingRestaurantsData },
  top_rated: { GET: ApiResponse_TrendingRestaurantsData },
  gemini_search: { POST: ApiResponse_GeminiSearchData },
  summarize_snipe_logs: { POST: ApiResponse_SummaryData },
  start_resy_onboarding: { POST: ApiResponse_OnboardingData },
  resy_account: {
    GET: ApiResponse_AccountStatusData,
    POST: ApiResponse_PaymentMethodUpdateData,
    DELETE: ApiResponse_DisconnectData,
  },
  reservation: { POST: ApiResponse_ReservationCreatedData },
  create_snipe: { POST: ApiResponse_JobCreatedData },
  update_snipe: { POST: ApiResponse_JobUpdatedData },
  cancel_snipe: { POST: ApiResponse_JobCancelledData },
} as const;

// Infer response types from schemas
export type MeResponse = z.infer<typeof ApiResponse_MeData>;
export type VenueLinksApiResponse = z.infer<typeof ApiResponse_VenueLinksData>;
export type SearchApiResponse = z.infer<typeof ApiResponse_SearchData>;
export type VenueDetailResponse = z.infer<typeof ApiResponse_VenueDetailData>;
export type CalendarApiResponse = z.infer<typeof ApiResponse_CalendarData>;
export type SlotsApiResponse = z.infer<typeof ApiResponse_SlotsData>;
export type OnboardingApiResponse = z.infer<typeof ApiResponse_OnboardingData>;
export type AccountStatusApiResponse = z.infer<typeof ApiResponse_AccountStatusData>;
export type TrendingRestaurantsResponse = z.infer<typeof ApiResponse_TrendingRestaurantsData>;
export type GeminiSearchApiResponse = z.infer<typeof ApiResponse_GeminiSearchData>;
export type SummaryApiResponse = z.infer<typeof ApiResponse_SummaryData>;

// Component schemas from OpenAPI types
export type ApiSchemas = components["schemas"];

/**
 * Optional runtime validation - use in dev or for critical paths.
 * Validates API response against the schema and throws on mismatch.
 */
export function validateApiResponse<T extends z.ZodType>(
  schema: T,
  data: unknown
): z.infer<T> {
  const result = schema.safeParse(data);
  if (!result.success) {
    console.error("[API] Schema validation failed:", result.error.format());
    throw new Error(`API response validation failed: ${result.error.message}`);
  }
  return result.data;
}
