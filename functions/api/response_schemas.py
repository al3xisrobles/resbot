"""
Standardized response schemas for all API endpoints.
Using Pydantic models ensures compile-time validation of response structures.
"""
from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field, model_validator


# Generic type variable for data payload
T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper with success flag and optional data/error.
    
    All endpoints should return this structure:
    - Success: {"success": true, "data": {...}}
    - Error: {"success": false, "error": "message"}
    
    Usage:
        # Success response
        return ApiResponse(success=True, data={"result": "value"}).model_dump()
        
        # Error response
        return ApiResponse(success=False, error="Something went wrong").model_dump()
    """
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_response(self):
        """Ensure success responses have data and error responses have error message."""
        if self.success and self.data is None:
            raise ValueError("Success response must include 'data' field")
        if not self.success and self.error is None:
            raise ValueError("Error response must include 'error' field")
        if self.success and self.error is not None:
            raise ValueError("Success response should not include 'error' field")
        if not self.success and self.data is not None:
            raise ValueError("Error response should not include 'data' field")
        return self


class EmptyData(BaseModel):
    """Empty data object for responses that don't return specific data."""
    pass


# Specific response data models for different endpoints

class SummaryData(BaseModel):
    """Data model for summarize_snipe_logs endpoint."""
    summary: str = Field(..., description="AI-generated summary of reservation attempt")


class SnipeResultData(BaseModel):
    """Data model for run_snipe endpoint."""
    status: str = Field(..., description="Final status: 'done' or 'failed'")
    jobId: str = Field(..., description="Reservation job ID")
    resyToken: Optional[str] = Field(None, description="Resy confirmation token if successful")


class JobCreatedData(BaseModel):
    """Data model for create_snipe endpoint."""
    jobId: str = Field(..., description="Created reservation job ID")
    targetTimeIso: str = Field(..., description="ISO timestamp when snipe will execute")


class JobUpdatedData(BaseModel):
    """Data model for update_snipe endpoint."""
    jobId: str = Field(..., description="Updated reservation job ID")
    targetTimeIso: str = Field(..., description="ISO timestamp when snipe will execute")


class JobCancelledData(BaseModel):
    """Data model for cancel_snipe endpoint."""
    jobId: str = Field(..., description="Cancelled reservation job ID")


class ResyUserData(BaseModel):
    """Nested Resy user data for me endpoint."""
    email: str
    firstName: str
    lastName: str
    paymentMethodId: Optional[int] = None


class MeData(BaseModel):
    """Data model for /me endpoint."""
    onboardingStatus: str = Field(..., description="'not_started' or 'completed'")
    hasPaymentMethod: bool
    resy: Optional[ResyUserData] = None


class OnboardingData(BaseModel):
    """Data model for onboarding POST endpoint."""
    hasPaymentMethod: bool
    paymentMethodId: Optional[int] = None


class ResyPaymentMethod(BaseModel):
    """Payment method details for API responses."""
    id: int
    type: Optional[str] = None
    display: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: Optional[bool] = None
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    issuing_bank: Optional[str] = None


class AccountStatusData(BaseModel):
    """Data model for resy_account GET endpoint."""
    connected: bool
    hasPaymentMethod: Optional[bool] = None
    paymentMethods: Optional[list[ResyPaymentMethod]] = None
    paymentMethodId: Optional[int] = None
    email: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    mobileNumber: Optional[str] = None
    userId: Optional[int] = None  # Resy user ID


class PaymentMethodUpdateData(BaseModel):
    """Data model for payment method update."""
    message: str
    paymentMethodId: int


class DisconnectData(BaseModel):
    """Data model for account disconnect."""
    message: str


# Venue schemas
class VenueLinksModel(BaseModel):
    """Links for a venue (Google Maps, Resy)."""
    googleMaps: Optional[str] = None
    resy: Optional[str] = None


class VenueBasicData(BaseModel):
    """Basic venue info for venue links response."""
    name: str
    type: str
    address: str
    neighborhood: str
    priceRange: int
    rating: int


class VenueLinksData(BaseModel):
    """Data model for venue_links endpoint."""
    links: VenueLinksModel
    venueData: VenueBasicData


class VenueDetailData(BaseModel):
    """Data model for venue detail endpoint."""
    name: str
    venue_id: str
    type: str
    address: str
    neighborhood: str
    price_range: int
    rating: Optional[float] = None
    photoUrls: list[str] = Field(default_factory=list)
    description: str = ''


class VenuePaymentRequirementData(BaseModel):
    """Data model for check_venue_payment_requirement endpoint."""
    requiresPaymentMethod: Optional[bool] = None
    source: str
    slotsAnalyzed: Optional[int] = None


# Search schemas
class SearchResultItem(BaseModel):
    """Single search result item."""

    model_config = {'extra': 'allow'}  # Allow extra fields from Resy API

    id: str = ''
    name: str = ''
    locality: str = ''
    region: str = ''
    neighborhood: str = ''
    type: str = ''
    price_range: int = 0
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    imageUrl: Optional[str] = None
    availableTimes: Optional[list[str]] = None
    availabilityStatus: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def coerce_fields(cls, v: Any) -> Any:
        """Coerce Resy API response types to schema expectations."""
        if isinstance(v, dict):
            # Resy API returns id as int; coerce to str
            raw_id = v.get('id')
            if raw_id is not None and not isinstance(raw_id, str):
                v = {**v, 'id': str(raw_id)}
            # Resy API returns neighborhood as dict with 'name'; extract string
            nb = v.get('neighborhood')
            if isinstance(nb, dict) and 'name' in nb:
                v = {**v, 'neighborhood': nb['name']}
            elif isinstance(nb, dict):
                v = {**v, 'neighborhood': ''}
        return v


class SearchPagination(BaseModel):
    """Pagination info for search results."""
    offset: int
    perPage: int
    nextOffset: Optional[int] = None
    hasMore: bool
    total: Optional[int] = None
    isFiltered: Optional[bool] = None
    foundSoFar: Optional[int] = None


class SearchData(BaseModel):
    """Data model for search and search_map endpoints."""
    results: list[SearchResultItem]
    pagination: SearchPagination


# Calendar schemas
class CalendarAvailabilityEntry(BaseModel):
    """Single calendar availability entry."""
    date: str
    available: bool
    soldOut: bool
    closed: bool


class CalendarData(BaseModel):
    """Data model for calendar endpoint."""
    availability: list[CalendarAvailabilityEntry]
    startDate: str
    endDate: str


# Slots schema
class SlotsData(BaseModel):
    """Data model for slots endpoint."""
    times: list[str] = Field(default_factory=list)
    status: Optional[str] = None


# Reservation schemas
class ReservationCreatedData(BaseModel):
    """Data model for reservation POST endpoint."""
    message: str
    resy_token: Optional[str] = None


# Gemini search schemas
class GroundingChunkSegment(BaseModel):
    """Segment in grounding support."""
    startIndex: Optional[int] = None
    endIndex: Optional[int] = None
    text: Optional[str] = None


class GroundingSupportSegment(BaseModel):
    """Segment for grounding support."""
    startIndex: Optional[int] = None
    endIndex: Optional[int] = None
    text: Optional[str] = None


class GroundingChunkItem(BaseModel):
    """Single grounding chunk."""
    index: int
    title: str
    uri: Optional[str] = None
    snippet: Optional[str] = None


class GroundingSupportItem(BaseModel):
    """Single grounding support."""
    segment: GroundingSupportSegment
    groundingChunkIndices: list[int] = Field(default_factory=list)
    confidenceScores: list[float] = Field(default_factory=list)


class KeyFactItem(BaseModel):
    """Key fact with citation indices."""
    fact: str
    citationIndices: list[int] = Field(default_factory=list)


class GeminiSearchData(BaseModel):
    """Data model for gemini_search endpoint."""
    summary: str
    keyFacts: list[KeyFactItem] = Field(default_factory=list)
    webSearchQueries: list[str] = Field(default_factory=list)
    groundingChunks: list[GroundingChunkItem] = Field(default_factory=list)
    groundingSupports: list[GroundingSupportItem] = Field(default_factory=list)
    rawGroundingMetadata: Dict[str, Any] = Field(default_factory=dict)
    suggestedFollowUps: list[str] = Field(default_factory=list)


# Featured/Trending schemas
class TrendingRestaurantLocation(BaseModel):
    """Location for trending restaurant."""
    neighborhood: str
    locality: str
    region: str
    address: str


class TrendingRestaurantItem(BaseModel):
    """Single trending/climbing/top-rated restaurant."""
    id: str
    name: str
    type: str
    priceRange: int
    location: TrendingRestaurantLocation
    imageUrl: Optional[str] = None
    rating: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


# Type aliases for common response types
SummaryResponse = ApiResponse[SummaryData]
VenueLinksResponse = ApiResponse[VenueLinksData]
VenueDetailResponse = ApiResponse[VenueDetailData]
VenuePaymentRequirementResponse = ApiResponse[VenuePaymentRequirementData]
SearchResponse = ApiResponse[SearchData]
CalendarResponse = ApiResponse[CalendarData]
SlotsResponse = ApiResponse[SlotsData]
ReservationCreatedResponse = ApiResponse[ReservationCreatedData]
GeminiSearchResponse = ApiResponse[GeminiSearchData]
TrendingRestaurantsResponse = ApiResponse[list[TrendingRestaurantItem]]
SnipeResultResponse = ApiResponse[SnipeResultData]
JobCreatedResponse = ApiResponse[JobCreatedData]
JobUpdatedResponse = ApiResponse[JobUpdatedData]
JobCancelledResponse = ApiResponse[JobCancelledData]
MeResponse = ApiResponse[MeData]
OnboardingResponse = ApiResponse[OnboardingData]
AccountStatusResponse = ApiResponse[AccountStatusData]
PaymentMethodUpdateResponse = ApiResponse[PaymentMethodUpdateData]
DisconnectResponse = ApiResponse[DisconnectData]
EmptyResponse = ApiResponse[EmptyData]


def success_response(data: Any) -> Dict[str, Any]:
    """
    Helper to create a validated success response.
    
    Args:
        data: Response data (dict or Pydantic model)
        
    Returns:
        Validated response dict
        
    Raises:
        ValidationError if response structure is invalid
    """
    response = ApiResponse(success=True, data=data)
    return response.model_dump(exclude_none=True)


def error_response(error: str, status_code: int = 500) -> tuple[Dict[str, Any], int]:
    """
    Helper to create a validated error response with status code.
    
    Args:
        error: Error message
        status_code: HTTP status code (default 500)
        
    Returns:
        Tuple of (response_dict, status_code)
        
    Raises:
        ValidationError if response structure is invalid
    """
    response = ApiResponse(success=False, error=error)
    return response.model_dump(exclude_none=True), status_code
