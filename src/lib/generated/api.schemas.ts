import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";

const ResyUserData = z
  .object({
    email: z.string(),
    firstName: z.string(),
    lastName: z.string(),
    paymentMethodId: z.union([z.number(), z.null()]).optional().default(null),
  })
  .passthrough();
const MeData = z
  .object({
    onboardingStatus: z.string(),
    hasPaymentMethod: z.boolean(),
    resy: z.union([ResyUserData, z.null()]).optional().default(null),
  })
  .passthrough();
const ApiResponse_MeData = z
  .object({
    success: z.boolean(),
    data: MeData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const VenueDetailData = z
  .object({
    name: z.string(),
    venue_id: z.string(),
    type: z.string(),
    address: z.string(),
    neighborhood: z.string(),
    price_range: z.number().int(),
    rating: z.union([z.number(), z.null()]).optional().default(null),
    photoUrls: z.array(z.string()).optional(),
    description: z.string().optional().default(""),
  })
  .passthrough();
const ApiResponse_VenueDetailData = z
  .object({
    success: z.boolean(),
    data: VenueDetailData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const VenueLinksModel = z
  .object({
    googleMaps: z.union([z.string(), z.null()]).default(null),
    resy: z.union([z.string(), z.null()]).default(null),
  })
  .partial()
  .passthrough();
const VenueBasicData = z
  .object({
    name: z.string(),
    type: z.string(),
    address: z.string(),
    neighborhood: z.string(),
    priceRange: z.number().int(),
    rating: z.number().int(),
  })
  .passthrough();
const VenueLinksData = z
  .object({ links: VenueLinksModel, venueData: VenueBasicData })
  .passthrough();
const ApiResponse_VenueLinksData = z
  .object({
    success: z.boolean(),
    data: VenueLinksData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const VenuePaymentRequirementData = z
  .object({
    requiresPaymentMethod: z
      .union([z.boolean(), z.null()])
      .optional()
      .default(null),
    source: z.string(),
    slotsAnalyzed: z.union([z.number(), z.null()]).optional().default(null),
  })
  .passthrough();
const ApiResponse_VenuePaymentRequirementData = z
  .object({
    success: z.boolean(),
    data: VenuePaymentRequirementData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const SearchResultItem = z
  .object({
    id: z.string().default(""),
    name: z.string().default(""),
    locality: z.string().default(""),
    region: z.string().default(""),
    neighborhood: z.string().default(""),
    type: z.string().default(""),
    price_range: z.number().int().default(0),
    address: z.union([z.string(), z.null()]).default(null),
    latitude: z.union([z.number(), z.null()]).default(null),
    longitude: z.union([z.number(), z.null()]).default(null),
    imageUrl: z.union([z.string(), z.null()]).default(null),
    availableTimes: z.union([z.array(z.string()), z.null()]).default(null),
    availabilityStatus: z.union([z.string(), z.null()]).default(null),
  })
  .partial()
  .passthrough();
const SearchPagination = z
  .object({
    offset: z.number().int(),
    perPage: z.number().int(),
    nextOffset: z.union([z.number(), z.null()]).optional().default(null),
    hasMore: z.boolean(),
    total: z.union([z.number(), z.null()]).optional().default(null),
    isFiltered: z.union([z.boolean(), z.null()]).optional().default(null),
    foundSoFar: z.union([z.number(), z.null()]).optional().default(null),
  })
  .passthrough();
const SearchData = z
  .object({ results: z.array(SearchResultItem), pagination: SearchPagination })
  .passthrough();
const ApiResponse_SearchData = z
  .object({
    success: z.boolean(),
    data: SearchData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const CalendarAvailabilityEntry = z
  .object({
    date: z.string(),
    available: z.boolean(),
    soldOut: z.boolean(),
    closed: z.boolean(),
  })
  .passthrough();
const CalendarData = z
  .object({
    availability: z.array(CalendarAvailabilityEntry),
    startDate: z.string(),
    endDate: z.string(),
  })
  .passthrough();
const ApiResponse_CalendarData = z
  .object({
    success: z.boolean(),
    data: CalendarData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const SlotsData = z
  .object({
    times: z.array(z.string()),
    status: z.union([z.string(), z.null()]).default(null),
  })
  .partial()
  .passthrough();
const ApiResponse_SlotsData = z
  .object({
    success: z.boolean(),
    data: SlotsData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const ReservationCreatedData = z
  .object({
    message: z.string(),
    resy_token: z.union([z.string(), z.null()]).optional().default(null),
  })
  .passthrough();
const ApiResponse_ReservationCreatedData = z
  .object({
    success: z.boolean(),
    data: ReservationCreatedData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const KeyFactItem = z
  .object({
    fact: z.string(),
    citationIndices: z.array(z.number().int()).optional(),
  })
  .passthrough();
const GroundingChunkItem = z
  .object({
    index: z.number().int(),
    title: z.string(),
    uri: z.union([z.string(), z.null()]).optional().default(null),
    snippet: z.union([z.string(), z.null()]).optional().default(null),
  })
  .passthrough();
const GroundingSupportSegment = z
  .object({
    startIndex: z.union([z.number(), z.null()]).default(null),
    endIndex: z.union([z.number(), z.null()]).default(null),
    text: z.union([z.string(), z.null()]).default(null),
  })
  .partial()
  .passthrough();
const GroundingSupportItem = z
  .object({
    segment: GroundingSupportSegment,
    groundingChunkIndices: z.array(z.number().int()).optional(),
    confidenceScores: z.array(z.number()).optional(),
  })
  .passthrough();
const GeminiSearchData = z
  .object({
    summary: z.string(),
    keyFacts: z.array(KeyFactItem).optional(),
    webSearchQueries: z.array(z.string()).optional(),
    groundingChunks: z.array(GroundingChunkItem).optional(),
    groundingSupports: z.array(GroundingSupportItem).optional(),
    rawGroundingMetadata: z.object({}).partial().passthrough().optional(),
    suggestedFollowUps: z.array(z.string()).optional(),
  })
  .passthrough();
const ApiResponse_GeminiSearchData = z
  .object({
    success: z.boolean(),
    data: GeminiSearchData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const TrendingRestaurantLocation = z
  .object({
    neighborhood: z.string(),
    locality: z.string(),
    region: z.string(),
    address: z.string(),
  })
  .passthrough();
const TrendingRestaurantItem = z
  .object({
    id: z.string(),
    name: z.string(),
    type: z.string(),
    priceRange: z.number().int(),
    location: TrendingRestaurantLocation,
    imageUrl: z.union([z.string(), z.null()]).optional().default(null),
    rating: z.union([z.number(), z.null()]).optional().default(null),
    lat: z.union([z.number(), z.null()]).optional().default(null),
    lng: z.union([z.number(), z.null()]).optional().default(null),
  })
  .passthrough();
const ApiResponse_TrendingRestaurantsData = z
  .object({
    success: z.boolean(),
    data: z.array(TrendingRestaurantItem).optional(),
    error: z.string().optional(),
  })
  .passthrough();
const OnboardingData = z
  .object({
    hasPaymentMethod: z.boolean(),
    paymentMethodId: z.union([z.number(), z.null()]).optional().default(null),
  })
  .passthrough();
const ApiResponse_OnboardingData = z
  .object({
    success: z.boolean(),
    data: OnboardingData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const ResyPaymentMethod = z
  .object({ id: z.number().int(), type: z.string() })
  .passthrough();
const AccountStatusData = z
  .object({
    connected: z.boolean(),
    hasPaymentMethod: z.union([z.boolean(), z.null()]).optional().default(null),
    paymentMethods: z
      .union([z.array(ResyPaymentMethod), z.null()])
      .optional()
      .default(null),
    paymentMethodId: z.union([z.number(), z.null()]).optional().default(null),
    email: z.union([z.string(), z.null()]).optional().default(null),
    firstName: z.union([z.string(), z.null()]).optional().default(null),
    lastName: z.union([z.string(), z.null()]).optional().default(null),
    mobileNumber: z.union([z.string(), z.null()]).optional().default(null),
    userId: z.union([z.number(), z.null()]).optional().default(null),
  })
  .passthrough();
const ApiResponse_AccountStatusData = z
  .object({
    success: z.boolean(),
    data: AccountStatusData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const PaymentMethodUpdateData = z
  .object({ message: z.string(), paymentMethodId: z.number().int() })
  .passthrough();
const ApiResponse_PaymentMethodUpdateData = z
  .object({
    success: z.boolean(),
    data: PaymentMethodUpdateData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const DisconnectData = z.object({ message: z.string() }).passthrough();
const ApiResponse_DisconnectData = z
  .object({
    success: z.boolean(),
    data: DisconnectData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const SummaryData = z.object({ summary: z.string() }).passthrough();
const ApiResponse_SummaryData = z
  .object({
    success: z.boolean(),
    data: SummaryData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const JobCreatedData = z
  .object({ jobId: z.string(), targetTimeIso: z.string() })
  .passthrough();
const ApiResponse_JobCreatedData = z
  .object({
    success: z.boolean(),
    data: JobCreatedData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const JobUpdatedData = z
  .object({ jobId: z.string(), targetTimeIso: z.string() })
  .passthrough();
const ApiResponse_JobUpdatedData = z
  .object({
    success: z.boolean(),
    data: JobUpdatedData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const JobCancelledData = z.object({ jobId: z.string() }).passthrough();
const ApiResponse_JobCancelledData = z
  .object({
    success: z.boolean(),
    data: JobCancelledData.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const SnipeResultData = z
  .object({
    status: z.string(),
    jobId: z.string(),
    resyToken: z.union([z.string(), z.null()]).optional().default(null),
  })
  .passthrough();
const ApiResponse_TrendingRestaurantItem = z
  .object({
    success: z.boolean(),
    data: TrendingRestaurantItem.optional(),
    error: z.string().optional(),
  })
  .passthrough();
const ApiResponse_SnipeResultData = z
  .object({
    success: z.boolean(),
    data: SnipeResultData.optional(),
    error: z.string().optional(),
  })
  .passthrough();

export const schemas = {
  ResyUserData,
  MeData,
  ApiResponse_MeData,
  VenueDetailData,
  ApiResponse_VenueDetailData,
  VenueLinksModel,
  VenueBasicData,
  VenueLinksData,
  ApiResponse_VenueLinksData,
  VenuePaymentRequirementData,
  ApiResponse_VenuePaymentRequirementData,
  SearchResultItem,
  SearchPagination,
  SearchData,
  ApiResponse_SearchData,
  CalendarAvailabilityEntry,
  CalendarData,
  ApiResponse_CalendarData,
  SlotsData,
  ApiResponse_SlotsData,
  ReservationCreatedData,
  ApiResponse_ReservationCreatedData,
  KeyFactItem,
  GroundingChunkItem,
  GroundingSupportSegment,
  GroundingSupportItem,
  GeminiSearchData,
  ApiResponse_GeminiSearchData,
  TrendingRestaurantLocation,
  TrendingRestaurantItem,
  ApiResponse_TrendingRestaurantsData,
  OnboardingData,
  ApiResponse_OnboardingData,
  ResyPaymentMethod,
  AccountStatusData,
  ApiResponse_AccountStatusData,
  PaymentMethodUpdateData,
  ApiResponse_PaymentMethodUpdateData,
  DisconnectData,
  ApiResponse_DisconnectData,
  SummaryData,
  ApiResponse_SummaryData,
  JobCreatedData,
  ApiResponse_JobCreatedData,
  JobUpdatedData,
  ApiResponse_JobUpdatedData,
  JobCancelledData,
  ApiResponse_JobCancelledData,
  SnipeResultData,
  ApiResponse_TrendingRestaurantItem,
  ApiResponse_SnipeResultData,
};

const endpoints = makeApi([
  {
    method: "get",
    path: "/calendar",
    alias: "getCalendar",
    requestFormat: "json",
    response: ApiResponse_CalendarData,
  },
  {
    method: "post",
    path: "/cancel_snipe",
    alias: "postCancel_snipe",
    requestFormat: "json",
    response: ApiResponse_JobCancelledData,
  },
  {
    method: "get",
    path: "/check_venue_payment_requirement",
    alias: "getCheck_venue_payment_requirement",
    requestFormat: "json",
    response: ApiResponse_VenuePaymentRequirementData,
  },
  {
    method: "get",
    path: "/climbing",
    alias: "getClimbing",
    requestFormat: "json",
    response: ApiResponse_TrendingRestaurantsData,
  },
  {
    method: "post",
    path: "/create_snipe",
    alias: "postCreate_snipe",
    requestFormat: "json",
    response: ApiResponse_JobCreatedData,
  },
  {
    method: "post",
    path: "/gemini_search",
    alias: "postGemini_search",
    requestFormat: "json",
    response: ApiResponse_GeminiSearchData,
  },
  {
    method: "get",
    path: "/me",
    alias: "getMe",
    requestFormat: "json",
    response: ApiResponse_MeData,
  },
  {
    method: "post",
    path: "/reservation",
    alias: "postReservation",
    requestFormat: "json",
    response: ApiResponse_ReservationCreatedData,
  },
  {
    method: "get",
    path: "/resy_account",
    alias: "getResy_account",
    requestFormat: "json",
    response: ApiResponse_AccountStatusData,
  },
  {
    method: "post",
    path: "/resy_account",
    alias: "postResy_account",
    requestFormat: "json",
    response: ApiResponse_PaymentMethodUpdateData,
  },
  {
    method: "delete",
    path: "/resy_account",
    alias: "deleteResy_account",
    requestFormat: "json",
    response: ApiResponse_DisconnectData,
  },
  {
    method: "get",
    path: "/search",
    alias: "getSearch",
    requestFormat: "json",
    response: ApiResponse_SearchData,
  },
  {
    method: "get",
    path: "/search_map",
    alias: "getSearch_map",
    requestFormat: "json",
    response: ApiResponse_SearchData,
  },
  {
    method: "get",
    path: "/slots",
    alias: "getSlots",
    requestFormat: "json",
    response: ApiResponse_SlotsData,
  },
  {
    method: "post",
    path: "/start_resy_onboarding",
    alias: "postStart_resy_onboarding",
    requestFormat: "json",
    response: ApiResponse_OnboardingData,
  },
  {
    method: "post",
    path: "/summarize_snipe_logs",
    alias: "postSummarize_snipe_logs",
    requestFormat: "json",
    response: ApiResponse_SummaryData,
  },
  {
    method: "get",
    path: "/top_rated",
    alias: "getTop_rated",
    requestFormat: "json",
    response: ApiResponse_TrendingRestaurantsData,
  },
  {
    method: "post",
    path: "/update_snipe",
    alias: "postUpdate_snipe",
    requestFormat: "json",
    response: ApiResponse_JobUpdatedData,
  },
  {
    method: "get",
    path: "/venue",
    alias: "getVenue",
    requestFormat: "json",
    response: ApiResponse_VenueDetailData,
  },
  {
    method: "get",
    path: "/venue_links",
    alias: "getVenue_links",
    requestFormat: "json",
    response: ApiResponse_VenueLinksData,
  },
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, options);
}
