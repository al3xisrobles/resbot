from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ResyConfig(BaseModel):
    api_key: str
    token: str
    payment_method_id: Optional[int] = None
    email: Optional[str] = None
    password: Optional[str] = None
    retry_on_taken_slot: bool = True

    def get_authorization(self) -> str:
        return f'ResyAPI api_key="{self.api_key}"'


class ReservationRequest(BaseModel):
    venue_id: str
    party_size: int
    ideal_hour: int
    ideal_minute: int
    window_hours: int
    prefer_early: bool
    preferred_type: Optional[str] = None
    ideal_date: Optional[date] = None
    days_in_advance: Optional[int] = None

    @model_validator(mode='before')
    @classmethod
    def validate_target_date(cls, data: Dict) -> Dict:
        has_date = data.get("ideal_date") is not None
        has_waiting_pd = data.get("days_in_advance") is not None

        if has_date and has_waiting_pd:
            raise ValueError("Must only provide one of ideal_date or days_in_advance")
        if has_date or has_waiting_pd:
            return data

        raise ValueError("Must provide ideal_date or days_in_advance")

    @property
    def target_date(self) -> date:
        if self.ideal_date:
            return self.ideal_date

        if self.days_in_advance:
            return date.today() + timedelta(days=self.days_in_advance)

        raise ValueError("No date")


class ReservationRetriesConfig(BaseModel):
    seconds_between_retries: float
    n_retries: int


class TimedReservationRequest(BaseModel):
    reservation_request: ReservationRequest
    expected_drop_hour: int
    expected_drop_minute: int


class AuthRequestBody(BaseModel):
    email: str
    password: str


class PaymentMethod(BaseModel):
    """Payment method from Resy /4/auth/password response."""
    id: int
    type: Optional[str] = None
    display: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: Optional[bool] = None
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    issuing_bank: Optional[str] = None


class AuthResponseBody(BaseModel):
    model_config = ConfigDict(extra='allow')  # Allow extra fields from Resy API
    payment_methods: List[PaymentMethod]
    token: str
    payment_method_id: Optional[int] = None
    em_address: Optional[str] = None  # User email
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    guest_id: Optional[int] = None  # Resy guest ID
    id: Optional[int] = None  # Resy user ID
    mobile_number: Optional[str] = None
    legacy_token: Optional[str] = None


class FindRequestBody(BaseModel):
    lat: int = 0
    long: int = 0
    day: str
    party_size: int
    venue_id: Optional[int] = None

    @field_validator("day")
    @classmethod
    def validate_day(cls, day: str) -> str:
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Day must be in isoformat") from exc

        return day


class SlotConfig(BaseModel):
    model_config = ConfigDict(extra='allow')  # Allow extra fields

    id: int | str  # Can be either int or str depending on API version
    type: str
    token: str


class SlotDate(BaseModel):
    start: datetime
    end: datetime


class SlotPayment(BaseModel):
    """Payment info from /find slot; used to detect if venue requires payment method."""
    model_config = ConfigDict(extra='allow')
    is_paid: bool = False
    deposit_fee: Optional[Any] = None
    cancellation_fee: Optional[Any] = None


class Slot(BaseModel):
    model_config = ConfigDict(extra='allow')
    config: SlotConfig
    date: SlotDate
    payment: Optional[SlotPayment] = None


class Venue(BaseModel):
    model_config = ConfigDict(extra='allow')  # Allow extra fields like 'venue' metadata
    slots: List[Slot] = []
    templates: Optional[Dict[str, Any]] = None  # template_id -> {is_paid, deposit_fee, ...}


class Results(BaseModel):
    venues: List[Venue]


class FindResponseBody(BaseModel):
    results: Results


class DetailsRequestBody(BaseModel):
    config_id: str
    party_size: int
    day: str


class BookToken(BaseModel):
    date_expires: datetime
    value: str


class DetailsResponseBody(BaseModel):
    book_token: BookToken


class BookRequestBody(BaseModel):
    book_token: str
    struct_payment_method: PaymentMethod
    source_id: str = "resy.com-venue-details"


class BookResponseBody(BaseModel):
    resy_token: str


# --- Calendar (/4/venue/calendar) ---


class CalendarRequestParams(BaseModel):
    """Query params for GET /4/venue/calendar."""

    venue_id: str
    num_seats: int = 2
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD


class CalendarInventory(BaseModel):
    model_config = ConfigDict(extra="allow")
    reservation: Optional[str] = None  # 'available', 'sold-out', 'closed', etc.


class CalendarEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    date: str
    inventory: Optional[CalendarInventory] = None


class CalendarResponseBody(BaseModel):
    model_config = ConfigDict(extra="allow")
    scheduled: List[CalendarEntry] = []


# --- Venue (/3/venue) ---


class VenueLocation(BaseModel):
    model_config = ConfigDict(extra="allow")
    address_1: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VenueResponseBody(BaseModel):
    """Response from GET /3/venue. Fields we use + extra allowed."""

    model_config = ConfigDict(extra="allow")
    name: Optional[str] = None
    type: Optional[str] = None
    location: Optional[VenueLocation] = None
    images: List[Any] = []
    metadata: Optional[Dict[str, Any]] = None
    content: Optional[Any] = None  # List of content sections (name, body) or dict
    price_range_id: Optional[int] = None
    rater: Optional[List[Dict[str, Any]]] = None  # API returns list of rater objects


# --- Venue search advanced POST (/3/venuesearch/search) ---


class VenueSearchRequestBody(BaseModel):
    """POST body for /3/venuesearch/search (advanced search with geo, filters)."""

    model_config = ConfigDict(extra="allow")
    availability: bool = False
    page: int = 1
    per_page: int = 20
    geo: Dict[str, Any] = {}  # latitude, longitude, radius or bounding_box
    query: str = ""
    types: List[str] = ["venue"]
    order_by: Optional[str] = None
    highlight: Optional[Dict[str, str]] = None
    slot_filter: Optional[Dict[str, Any]] = None  # day, party_size


class VenueSearchHit(BaseModel):
    model_config = ConfigDict(extra="allow")
    _source: Optional[Dict[str, Any]] = None


class VenueSearchMeta(BaseModel):
    model_config = ConfigDict(extra="allow")
    total: int = 0


class VenueSearchResponseBody(BaseModel):
    """Response from POST /3/venuesearch/search."""

    model_config = ConfigDict(extra="allow")
    search: Optional[Dict[str, Any]] = None  # hits: List[VenueSearchHit]
    meta: Optional[VenueSearchMeta] = None


# --- City list (/3/cities/{slug}/list/{list_type}) ---


class CityListResults(BaseModel):
    model_config = ConfigDict(extra="allow")
    venues: List[Dict[str, Any]] = []


class CityListResponseBody(BaseModel):
    """Response from GET /3/cities/{slug}/list/climbing or top-rated."""

    model_config = ConfigDict(extra="allow")
    results: Optional[CityListResults] = None
