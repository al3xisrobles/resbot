import type { SearchPagination, SearchResult } from "@/lib/interfaces";

export type SearchMode = "browse" | "trending" | "top-rated" | "bookmarks";

export interface SearchFilters {
    query: string;
    cuisines: string[];
    priceRanges: string[];
    bookmarkedOnly: boolean;
    availableOnly: boolean;
    notReleasedOnly: boolean;
    mode: SearchMode;
}

export const CUISINES = [
    "All Cuisines",
    "Italian",
    "Japanese",
    "American",
    "French",
    "Chinese",
    "Mexican",
    "Mediterranean",
    "Indian",
    "Thai",
    "Korean",
    "Spanish",
    "Greek",
    "Vietnamese",
] as const;

export const PRICE_RANGES = [
    { label: "All Prices", value: "all" },
    { label: "$", value: "1" },
    { label: "$$", value: "2" },
    { label: "$$$", value: "3" },
    { label: "$$$$", value: "4" },
] as const;

export interface SearchSidebarProps {
    filters: SearchFilters;
    setFilters: React.Dispatch<React.SetStateAction<SearchFilters>>;
    searchResults: SearchResult[];
    loading: boolean;
    hasSearched: boolean;
    pagination: SearchPagination | null;
    currentPage: number;
    hasNextPage: boolean;
    inputsHaveChanged: boolean;
    onSearch: (page?: number) => void;
    onPageChange: (page: number) => void;
    onCardClick: (venueId: string) => void;
    onCardHover: (venueId: string | null) => void;
    onModeChange?: (mode: SearchMode) => void;
}
