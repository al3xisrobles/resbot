import React from "react";
import { format } from "date-fns";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Bookmark, Search, TrendingUp, Star, LogIn } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { TIME_SLOTS } from "@/lib/time-slots";
import { SearchResultItem } from "@/components/SearchResultItem";
import { SearchResultItemSkeleton } from "@/components/SearchResultItemSkeleton";
import { useAtom } from "jotai";
import { reservationFormAtom } from "@/atoms/reservationAtoms";
import { cityConfigAtom } from "@/atoms/cityAtom";
import {
    Pagination,
    PaginationContent,
    PaginationItem,
    PaginationLink,
    PaginationPrevious,
    PaginationNext,
    PaginationEllipsis,
} from "@/components/ui/pagination";
import { Separator } from "@/components/ui/separator";
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
} from "@/components/ui/sidebar";
import { Stack, Group } from "@/components/ui/layout";
import type { SearchSidebarProps, SearchMode } from "../lib/types";
import { CUISINES, PRICE_RANGES } from "../lib/types";
import { useAuth } from "@/contexts/AuthContext";

const TIME_SLOT_OPTIONS = TIME_SLOTS.map((slot) => (
    <SelectItem key={slot.value} value={slot.value}>
        {slot.display}
    </SelectItem>
));

export function SearchSidebar({
    filters,
    setFilters,
    searchResults,
    loading,
    hasSearched,
    pagination,
    currentPage,
    hasNextPage,
    onPageChange,
    onCardClick,
    onCardHover,
    onModeChange,
}: SearchSidebarProps) {
    const [reservationForm, setReservationForm] = useAtom(reservationFormAtom);
    const cityConfig = useAtom(cityConfigAtom)[0];
    const auth = useAuth();
    const navigate = useNavigate();
    const isAuthenticated = !!auth.currentUser;
    const selectedCuisines = React.useMemo(() => {
        if (filters.cuisines.length === 0) return "All Cuisines";
        if (filters.cuisines.length === 1) {
            return filters.cuisines[0] || "All Cuisines";
        }
        return filters.cuisines.filter((c) => c && (CUISINES as readonly string[]).includes(c)).join(", ");
    }, [filters.cuisines]);

    const selectedPriceRangeLabels = React.useMemo(() => {
        if (filters.priceRanges.length === 0) return "All Prices";
        if (filters.priceRanges.length === 1) {
            return (
                PRICE_RANGES.find((p) => p.value === filters.priceRanges[0])?.label ||
                "All Prices"
            );
        }
        return filters.priceRanges
            .map((val) => PRICE_RANGES.find((p) => p.value === val)?.label)
            .filter(Boolean)
            .join(", ");
    }, [filters.priceRanges]);

    const selectedAvailability = React.useMemo(() => {
        if (filters.availableOnly) return "Available Only";
        if (filters.notReleasedOnly) return "Not Released";
        return "Availability";
    }, [filters.availableOnly, filters.notReleasedOnly]);

    return (
        <Sidebar
            side="left"
            variant="sidebar"
            collapsible="none"
            className="border-r w-full md:w-(--sidebar-width)"
        >
            <SidebarContent className="no-scrollbar relative">
                {/* Login overlay for unauthenticated users */}
                {!isAuthenticated && (
                    <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-sm">
                        <div className="text-center space-y-4 px-8">
                            <LogIn className="size-12 mx-auto text-muted-foreground" />
                            <div className="space-y-2">
                                <h3 className="text-lg font-semibold">Login to search</h3>
                                <p className="text-sm text-muted-foreground max-w-sm">
                                    Sign in to search for restaurants and view availability
                                </p>
                            </div>
                            <Button
                                onClick={() => navigate("/login")}
                                className="mt-4"
                            >
                                <LogIn className="mr-2 size-4" />
                                Log in
                            </Button>
                        </div>
                    </div>
                )}

                <SidebarGroup className="p-0">
                    <SidebarGroupContent className="pb-4 px-4">
                        {/* Filter Card */}
                        <Card className="py-2 rounded-none border-0 border-b shadow-none">
                            <CardContent className="p-4">
                                <Stack itemsSpacing={12}>
                                    {/* Top Buttons: Bookmarks, Trending, Top Rated */}
                                    <Group itemsSpacing={32} itemsAlignX="center" noWrap className="flex-wrap py-4">
                                        <Stack itemsSpacing={4} itemsAlignX="center">
                                            <Button
                                                variant={filters.mode === "bookmarks" ? "secondary" : "outline"}
                                                className="w-16 h-16 rounded-full p-0 flex items-center justify-center"
                                                onClick={() => {
                                                    const newMode: SearchMode = filters.mode === "bookmarks" ? "browse" : "bookmarks";
                                                    setFilters({
                                                        ...filters,
                                                        mode: newMode,
                                                        bookmarkedOnly: newMode === "bookmarks",
                                                    });
                                                    onModeChange?.(newMode);
                                                }}
                                            >
                                                <Bookmark className="size-5" />
                                            </Button>
                                            <span className="text-xs text-center">Bookmarks</span>
                                        </Stack>
                                        <Stack itemsSpacing={4} itemsAlignX="center">
                                            <Button
                                                variant={filters.mode === "trending" ? "secondary" : "outline"}
                                                className="w-16 h-16 rounded-full p-0 flex items-center justify-center"
                                                onClick={() => {
                                                    const newMode: SearchMode = filters.mode === "trending" ? "browse" : "trending";
                                                    setFilters({
                                                        ...filters,
                                                        mode: newMode,
                                                    });
                                                    onModeChange?.(newMode);
                                                }}
                                            >
                                                <TrendingUp className="size-5" />
                                            </Button>
                                            <span className="text-xs text-center">Trending</span>
                                        </Stack>
                                        <Stack itemsSpacing={4} itemsAlignX="center">
                                            <Button
                                                variant={filters.mode === "top-rated" ? "secondary" : "outline"}
                                                className="w-16 h-16 rounded-full p-0 flex items-center justify-center"
                                                onClick={() => {
                                                    const newMode: SearchMode = filters.mode === "top-rated" ? "browse" : "top-rated";
                                                    setFilters({
                                                        ...filters,
                                                        mode: newMode,
                                                    });
                                                    onModeChange?.(newMode);
                                                }}
                                            >
                                                <Star className="size-5" />
                                            </Button>
                                            <span className="text-xs text-center">Top Rated</span>
                                        </Stack>
                                    </Group>

                                    {/* Reservation Inputs (Left) + Dropdowns (Right) */}
                                    <Group itemsSpacing={8} itemsAlignX="space-between" noWrap className="flex-wrap">
                                        {/* Reservation Inputs - Circular */}
                                        <Group itemsSpacing={4} noWrap className="flex-wrap">
                                            {/* Party Size */}
                                            <Select
                                                value={reservationForm.partySize}
                                                onValueChange={(value) =>
                                                    setReservationForm({
                                                        ...reservationForm,
                                                        partySize: value,
                                                    })
                                                }
                                            >
                                                <SelectTrigger id="party-size-browse" className="h-9 rounded-full px-4">
                                                    <SelectValue placeholder="Size" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {Array.from({ length: 6 }, (_, i) => i + 1).map(
                                                        (size) => (
                                                            <SelectItem key={size} value={size.toString()}>
                                                                {size} {size === 1 ? "person" : "people"}
                                                            </SelectItem>
                                                        )
                                                    )}
                                                </SelectContent>
                                            </Select>

                                            {/* Date */}
                                            <Popover>
                                                <PopoverTrigger asChild>
                                                    <button
                                                        className={cn(
                                                            "flex h-9 items-center justify-center rounded-full border bg-background px-4 py-2 text-sm shadow-xs ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors whitespace-nowrap",
                                                            !reservationForm.date && "text-muted-foreground"
                                                        )}
                                                    >
                                                        {reservationForm.date ? (
                                                            format(reservationForm.date, "MMM d")
                                                        ) : (
                                                            <span>Date</span>
                                                        )}
                                                    </button>
                                                </PopoverTrigger>
                                                <PopoverContent className="w-auto p-0" align="start">
                                                    <Calendar
                                                        mode="single"
                                                        selected={reservationForm.date}
                                                        onSelect={(date) =>
                                                            setReservationForm({ ...reservationForm, date })
                                                        }
                                                    />
                                                </PopoverContent>
                                            </Popover>

                                            {/* Time */}
                                            <Select
                                                value={reservationForm.timeSlot}
                                                onValueChange={(value) =>
                                                    setReservationForm({
                                                        ...reservationForm,
                                                        timeSlot: value,
                                                    })
                                                }
                                            >
                                                <SelectTrigger id="time-browse" className="h-9 rounded-full px-4">
                                                    <SelectValue placeholder="Time" />
                                                </SelectTrigger>
                                                <SelectContent>{TIME_SLOT_OPTIONS}</SelectContent>
                                            </Select>
                                        </Group>

                                        {/* Dropdowns - Right Side */}
                                        <Group itemsSpacing={4} noWrap className="flex-wrap">
                                            {/* Availability Dropdown */}
                                            <Popover>
                                                <PopoverTrigger asChild>
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        className="border text-xs h-8 justify-between overflow-hidden rounded-full"
                                                    >
                                                        <span className="truncate">{selectedAvailability}</span>
                                                        <ChevronDown className="ml-1 size-3 opacity-50 shrink-0" />
                                                    </Button>
                                                </PopoverTrigger>
                                                <PopoverContent className="w-[200px] p-0" align="start">
                                                    <div className="p-2">
                                                        <div
                                                            className="flex items-center space-x-2 hover:bg-accent rounded-sm p-2 cursor-pointer"
                                                            onClick={() =>
                                                                setFilters({
                                                                    ...filters,
                                                                    availableOnly: !filters.availableOnly,
                                                                    notReleasedOnly: false,
                                                                })
                                                            }
                                                        >
                                                            <Checkbox
                                                                checked={filters.availableOnly}
                                                                onClick={(e) => e.stopPropagation()}
                                                                onCheckedChange={(checked) =>
                                                                    setFilters({
                                                                        ...filters,
                                                                        availableOnly: !!checked,
                                                                        notReleasedOnly: false,
                                                                    })
                                                                }
                                                            />
                                                            <span className="text-sm flex-1">
                                                                Available Only
                                                            </span>
                                                        </div>
                                                        <div
                                                            className="flex items-center space-x-2 hover:bg-accent rounded-sm p-2 cursor-pointer"
                                                            onClick={() =>
                                                                setFilters({
                                                                    ...filters,
                                                                    notReleasedOnly: !filters.notReleasedOnly,
                                                                    availableOnly: false,
                                                                })
                                                            }
                                                        >
                                                            <Checkbox
                                                                checked={filters.notReleasedOnly}
                                                                onClick={(e) => e.stopPropagation()}
                                                                onCheckedChange={(checked) =>
                                                                    setFilters({
                                                                        ...filters,
                                                                        notReleasedOnly: !!checked,
                                                                        availableOnly: false,
                                                                    })
                                                                }
                                                            />
                                                            <span className="text-sm flex-1">
                                                                Not Released
                                                            </span>
                                                        </div>
                                                    </div>
                                                </PopoverContent>
                                            </Popover>

                                            {/* Cuisine Multi-Select */}
                                            <Popover>
                                                <PopoverTrigger asChild>
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        className="border text-xs h-8 justify-between overflow-hidden rounded-full"
                                                    >
                                                        <span className="truncate">{selectedCuisines}</span>
                                                        <ChevronDown className="ml-1 size-3 opacity-50 shrink-0" />
                                                    </Button>
                                                </PopoverTrigger>
                                                <PopoverContent className="w-[200px] p-0" align="start">
                                                    <div className="max-h-[300px] overflow-y-auto p-2">
                                                        {CUISINES.filter((c) => c !== "All Cuisines").map(
                                                            (cuisine) => (
                                                                <div
                                                                    key={cuisine}
                                                                    className="flex items-center space-x-2 hover:bg-accent rounded-sm p-2 cursor-pointer"
                                                                    onClick={() => {
                                                                        const isSelected = filters.cuisines.includes(cuisine);
                                                                        setFilters({
                                                                            ...filters,
                                                                            cuisines: isSelected
                                                                                ? filters.cuisines.filter((c) => c !== cuisine)
                                                                                : [...filters.cuisines, cuisine],
                                                                        });
                                                                    }}
                                                                >
                                                                    <Checkbox
                                                                        checked={filters.cuisines.includes(cuisine)}
                                                                        onClick={(e) => e.stopPropagation()}
                                                                        onCheckedChange={(checked) => {
                                                                            if (checked) {
                                                                                setFilters({
                                                                                    ...filters,
                                                                                    cuisines: [
                                                                                        ...filters.cuisines,
                                                                                        cuisine,
                                                                                    ],
                                                                                });
                                                                            } else {
                                                                                setFilters({
                                                                                    ...filters,
                                                                                    cuisines: filters.cuisines.filter(
                                                                                        (c) => c !== cuisine
                                                                                    ),
                                                                                });
                                                                            }
                                                                        }}
                                                                    />
                                                                    <span className="text-sm flex-1">
                                                                        {cuisine}
                                                                    </span>
                                                                </div>
                                                            )
                                                        )}
                                                    </div>
                                                </PopoverContent>
                                            </Popover>

                                            {/* Price Range Multi-Select */}
                                            <Popover>
                                                <PopoverTrigger asChild>
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        className="border text-xs h-8 justify-between overflow-hidden rounded-full"
                                                    >
                                                        <span className="truncate">
                                                            {selectedPriceRangeLabels}
                                                        </span>
                                                        <ChevronDown className="ml-1 size-3 opacity-50 shrink-0" />
                                                    </Button>
                                                </PopoverTrigger>
                                                <PopoverContent className="w-[200px] p-0" align="start">
                                                    <div className="max-h-[300px] overflow-y-auto p-2">
                                                        {PRICE_RANGES.filter((p) => p.value !== "all").map(
                                                            (price) => (
                                                                <div
                                                                    key={price.value}
                                                                    className="flex items-center space-x-2 hover:bg-accent rounded-sm p-2 cursor-pointer"
                                                                    onClick={() => {
                                                                        const isSelected = filters.priceRanges.includes(price.value);
                                                                        setFilters({
                                                                            ...filters,
                                                                            priceRanges: isSelected
                                                                                ? filters.priceRanges.filter((p) => p !== price.value)
                                                                                : [...filters.priceRanges, price.value],
                                                                        });
                                                                    }}
                                                                >
                                                                    <Checkbox
                                                                        checked={filters.priceRanges.includes(
                                                                            price.value
                                                                        )}
                                                                        onClick={(e) => e.stopPropagation()}
                                                                        onCheckedChange={(checked) => {
                                                                            if (checked) {
                                                                                setFilters({
                                                                                    ...filters,
                                                                                    priceRanges: [
                                                                                        ...filters.priceRanges,
                                                                                        price.value,
                                                                                    ],
                                                                                });
                                                                            } else {
                                                                                setFilters({
                                                                                    ...filters,
                                                                                    priceRanges:
                                                                                        filters.priceRanges.filter(
                                                                                            (p) => p !== price.value
                                                                                        ),
                                                                                });
                                                                            }
                                                                        }}
                                                                    />
                                                                    <span className="text-sm flex-1">
                                                                        {price.label}
                                                                    </span>
                                                                </div>
                                                            )
                                                        )}
                                                    </div>
                                                </PopoverContent>
                                            </Popover>
                                        </Group>
                                    </Group>
                                </Stack>
                            </CardContent>
                        </Card>

                        {/* Search Results */}
                        <Stack itemsSpacing={16}>
                            {loading && (
                                <Stack itemsSpacing={4} className="mt-4">
                                    {Array.from({ length: 20 }).map((_, index) => (
                                        <SearchResultItemSkeleton key={index} />
                                    ))}
                                </Stack>
                            )}

                            {!loading && hasSearched && searchResults.length === 0 && (
                                <Stack itemsSpacing={8} itemsAlignX="center">
                                    <div className="text-center py-8 text-muted-foreground">
                                        No restaurants found. Try a different search.
                                    </div>
                                    {currentPage > 1 && (
                                        <Button variant="outline" onClick={() => onPageChange(1)}>
                                            Go back to first page
                                        </Button>
                                    )}
                                </Stack>
                            )}

                            {!loading && searchResults.length > 0 && (
                                <Stack itemsSpacing={12} className="mt-4">
                                    <p className="text-sm text-muted-foreground">
                                        Found {pagination?.total || searchResults.length} restaurant
                                        {(pagination?.total || searchResults.length) !== 1
                                            ? "s"
                                            : ""}
                                        {pagination && pagination.total && pagination.perPage && (
                                            <span className="pl-4"> Page {currentPage} of {Math.ceil(pagination.total / pagination.perPage)}</span>
                                        )}
                                    </p>
                                    <Stack itemsSpacing={4}>
                                        {searchResults.map((result) => {
                                            const hasAllReservationDetails =
                                                reservationForm.date &&
                                                reservationForm.timeSlot &&
                                                reservationForm.partySize;

                                            const hasAvailabilityParams =
                                                reservationForm.date && reservationForm.partySize;

                                            return (
                                                <div key={result.id}>
                                                    <SearchResultItem
                                                        id={result.id}
                                                        name={result.name}
                                                        type={result.type}
                                                        priceRange={result.price_range}
                                                        location={[
                                                            result.neighborhood,
                                                            result.locality,
                                                            result.region,
                                                        ]
                                                            .filter(Boolean)
                                                            .filter((item) => item !== "N/A")
                                                            .join(", ")}
                                                        imageUrl={result.imageUrl || null}
                                                        onCardClick={onCardClick}
                                                        onHover={onCardHover}
                                                        showPlaceholder={!hasAllReservationDetails}
                                                        availableTimes={
                                                            hasAvailabilityParams
                                                                ? result.availableTimes
                                                                : undefined
                                                        }
                                                        availabilityStatus={
                                                            hasAvailabilityParams
                                                                ? result.availabilityStatus
                                                                : undefined
                                                        }
                                                    />
                                                    <Separator className="my-2" />
                                                </div>
                                            );
                                        })}
                                    </Stack>
                                </Stack>
                            )}

                            {!loading && !hasSearched && (
                                <Stack itemsSpacing={12} itemsAlignX="center" className="py-12">
                                    <Search className="size-12 mx-auto text-muted-foreground" />
                                    <Stack itemsSpacing={8} itemsAlignX="center">
                                        <h3 className="text-lg font-medium">
                                            Search for Restaurants
                                        </h3>
                                        <p className="text-sm text-muted-foreground max-w-[280px] text-center">
                                            Enter a restaurant name and customize your filters to find
                                            the perfect dining experience in {cityConfig.name}
                                        </p>
                                    </Stack>
                                </Stack>
                            )}
                        </Stack>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>

            {/* Pagination Footer */}
            {pagination &&
                (() => {
                    // Show pagination if:
                    // 1. We're loading (show previous pagination state), OR
                    // 2. We have results and pagination conditions are met
                    if (loading) {
                        // Show pagination while loading if we have pagination data
                        return currentPage > 1 || hasNextPage || (pagination.total !== undefined && pagination.total > 0) || pagination.isFiltered;
                    }
                    // Normal pagination logic when not loading
                    if (searchResults.length > 0) {
                        if (currentPage > 1 || hasNextPage) return true;
                        if (pagination.isFiltered) return true;
                        if (pagination.total !== undefined && pagination.total > 0) {
                            const totalPages = Math.ceil(pagination.total / pagination.perPage);
                            return totalPages > 1;
                        }
                    }
                    return false;
                })() && (
                    <SidebarFooter className="border-t p-2">
                        {/* Progressive pagination UI for filtered results */}
                        {pagination.isFiltered ? (
                            <div className="flex items-center justify-between px-2">
                                <span className="text-sm text-muted-foreground">
                                    {pagination.foundSoFar}+ found
                                    {loading && " (checking more...)"}
                                </span>
                                <div className="flex items-center gap-2">
                                    {currentPage > 1 && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => onPageChange(currentPage - 1)}
                                            disabled={loading}
                                        >
                                            Previous
                                        </Button>
                                    )}
                                    {hasNextPage && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => onPageChange(currentPage + 1)}
                                            disabled={loading}
                                        >
                                            {loading ? "Loading..." : "Load More"}
                                        </Button>
                                    )}
                                </div>
                            </div>
                        ) : (
                            /* Standard pagination UI with page numbers */
                            <Pagination>
                                <PaginationContent>
                                    <PaginationItem>
                                        <PaginationPrevious
                                            href="#"
                                            onClick={(e) => {
                                                e.preventDefault();
                                                if (!loading && currentPage > 1) {
                                                    onPageChange(currentPage - 1);
                                                }
                                            }}
                                            className={
                                                loading || currentPage === 1
                                                    ? "pointer-events-none opacity-50"
                                                    : ""
                                            }
                                        />
                                    </PaginationItem>

                                    {(() => {
                                        // If we have total, calculate and show page numbers
                                        if (pagination.total !== undefined && pagination.total > 0) {
                                            const totalPages = Math.ceil(pagination.total / pagination.perPage);
                                            const pages: (number | "ellipsis")[] = [];

                                            // Always show first page
                                            if (totalPages <= 7) {
                                                // Show all pages if 7 or fewer
                                                for (let i = 1; i <= totalPages; i++) {
                                                    pages.push(i);
                                                }
                                            } else {
                                                // Show first page
                                                pages.push(1);

                                                if (currentPage <= 3) {
                                                    // Near the beginning: show 1, 2, 3, 4, ..., last
                                                    for (let i = 2; i <= 4; i++) {
                                                        pages.push(i);
                                                    }
                                                    pages.push("ellipsis");
                                                    pages.push(totalPages);
                                                } else if (currentPage >= totalPages - 2) {
                                                    // Near the end: show 1, ..., last-3, last-2, last-1, last
                                                    pages.push("ellipsis");
                                                    for (let i = totalPages - 3; i <= totalPages; i++) {
                                                        pages.push(i);
                                                    }
                                                } else {
                                                    // In the middle: show 1, ..., current-1, current, current+1, ..., last
                                                    pages.push("ellipsis");
                                                    for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                                                        pages.push(i);
                                                    }
                                                    pages.push("ellipsis");
                                                    pages.push(totalPages);
                                                }
                                            }

                                            return pages.map((page, index) => {
                                                if (page === "ellipsis") {
                                                    return (
                                                        <PaginationItem key={`ellipsis-${index}`}>
                                                            <PaginationEllipsis />
                                                        </PaginationItem>
                                                    );
                                                }
                                                return (
                                                    <PaginationItem key={page}>
                                                        <PaginationLink
                                                            href="#"
                                                            onClick={(e) => {
                                                                e.preventDefault();
                                                                if (!loading && page !== currentPage) {
                                                                    onPageChange(page);
                                                                }
                                                            }}
                                                            isActive={page === currentPage}
                                                            className={loading ? "pointer-events-none opacity-50" : ""}
                                                        >
                                                            {page}
                                                        </PaginationLink>
                                                    </PaginationItem>
                                                );
                                            });
                                        } else {
                                            // Fallback: show current page only (original implementation)
                                            return (
                                                <>
                                                    <PaginationItem>
                                                        <PaginationLink
                                                            href="#"
                                                            onClick={(e) => e.preventDefault()}
                                                            isActive={true}
                                                            className={loading ? "pointer-events-none opacity-50" : ""}
                                                        >
                                                            {currentPage}
                                                        </PaginationLink>
                                                    </PaginationItem>
                                                    {hasNextPage && (
                                                        <PaginationItem>
                                                            <PaginationEllipsis />
                                                        </PaginationItem>
                                                    )}
                                                </>
                                            );
                                        }
                                    })()}

                                    <PaginationItem>
                                        <PaginationNext
                                            href="#"
                                            onClick={(e) => {
                                                e.preventDefault();
                                                if (!loading && hasNextPage) {
                                                    onPageChange(currentPage + 1);
                                                }
                                            }}
                                            className={
                                                loading || !hasNextPage
                                                    ? "pointer-events-none opacity-50"
                                                    : ""
                                            }
                                        />
                                    </PaginationItem>
                                </PaginationContent>
                            </Pagination>
                        )}
                    </SidebarFooter>
                )}
        </Sidebar>
    );
}
