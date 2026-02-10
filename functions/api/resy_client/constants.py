from enum import Enum


RESY_BASE_URL = "https://api.resy.com"
N_RETRIES = 30
SECONDS_TO_WAIT_BETWEEN_RETRIES = 0.05


class ResyEndpoints(Enum):
    FIND = "/4/find"
    DETAILS = "/3/details"
    BOOK = "/3/book"
    PASSWORD_AUTH = "/4/auth/password"
    VENUE_SEARCH = "/3/venuesearch/search"
    CALENDAR = "/4/venue/calendar"
    VENUE = "/3/venue"
    CITY_LIST = "/3/cities/{slug}/list/{list_type}"
