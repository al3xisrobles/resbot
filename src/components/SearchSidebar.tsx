import React from "react";
import { format } from "date-fns";
import { Search, ChevronDown, Bookmark } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { TIME_SLOTS } from "@/lib/time-slots";
import { SearchResultItem } from "@/components/SearchResultItem";
import type { SearchPagination, SearchResult } from "@/lib/interfaces";
import { useAtom } from "jotai";
import { reservationFormAtom } from "@/atoms/reservationAtoms";
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

const TIME_SLOT_OPTIONS = TIME_SLOTS.map((slot) => (
  <SelectItem key={slot.value} value={slot.value}>
    {slot.display}
  </SelectItem>
));

const CUISINES = [
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
];

const PRICE_RANGES = [
  { label: "All Prices", value: "all" },
  { label: "$", value: "1" },
  { label: "$$", value: "2" },
  { label: "$$$", value: "3" },
  { label: "$$$$", value: "4" },
];

export interface SearchFilters {
  query: string;
  cuisines: string[];
  priceRanges: string[];
  bookmarkedOnly: boolean;
  availableOnly: boolean;
  notReleasedOnly: boolean;
}

interface SearchSidebarProps {
  filters: SearchFilters;
  setFilters: React.Dispatch<React.SetStateAction<SearchFilters>>;
  activeTab: string;
  setActiveTab: (tab: string) => void;
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
}

export function SearchSidebar({
  filters,
  setFilters,
  activeTab,
  setActiveTab,
  searchResults,
  loading,
  hasSearched,
  pagination,
  currentPage,
  hasNextPage,
  inputsHaveChanged,
  onSearch,
  onPageChange,
  onCardClick,
  onCardHover,
}: SearchSidebarProps) {
  const [reservationForm, setReservationForm] = useAtom(reservationFormAtom);
  const selectedCuisines = React.useMemo(() => {
    if (filters.cuisines.length === 0) return "All Cuisines";
    if (filters.cuisines.length === 1) {
      return filters.cuisines[0] || "All Cuisines";
    }
    return filters.cuisines.filter((c) => c && CUISINES.includes(c)).join(", ");
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

  return (
    <Sidebar
      side="left"
      variant="sidebar"
      collapsible="none"
      className="border-r w-full md:w-(--sidebar-width)"
    >
      <SidebarContent className="no-scrollbar">
        <SidebarGroup className="p-0">
          <SidebarGroupContent className="p-4">
            {/* Tabs & Filter Card */}
            <Card className="rounded-none border-0 border-b shadow-none">
              <CardContent className="p-4">
                <Tabs
                  value={activeTab}
                  onValueChange={setActiveTab}
                  className="w-full"
                >
                  <TabsList className="grid w-full grid-cols-2 mb-4">
                    <TabsTrigger value="browse">Browse</TabsTrigger>
                    <TabsTrigger value="specific">Search</TabsTrigger>
                  </TabsList>

                  {/* Tab: Specific Restaurant Search */}
                  <TabsContent value="specific" className="space-y-4 mt-0">
                    {/* Res Details */}
                    <div className="grid grid-cols-3 gap-3">
                      {/* Party Size */}
                      <div className="space-y-1.5">
                        <Label className="text-xs">Party Size</Label>
                        <Select
                          value={reservationForm.partySize}
                          onValueChange={(value) =>
                            setReservationForm({
                              ...reservationForm,
                              partySize: value,
                            })
                          }
                        >
                          <SelectTrigger id="party-size" className="h-9">
                            <SelectValue />
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
                      </div>

                      {/* Date */}
                      <div className="space-y-1.5">
                        <Label className="text-xs">Date</Label>
                        <Popover>
                          <PopoverTrigger asChild>
                            <button
                              className={cn(
                                "flex h-9 w-full items-center justify-start rounded-md border bg-background px-3 py-2 text-sm shadow-xs ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors"
                              )}
                            >
                              {reservationForm.date ? (
                                format(reservationForm.date, "MMM d")
                              ) : (
                                <span className="text-muted-foreground">
                                  Date
                                </span>
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
                      </div>

                      {/* Time */}
                      <div className="space-y-1.5">
                        <Label className="text-xs">Time</Label>
                        <Select
                          value={reservationForm.timeSlot}
                          onValueChange={(value) =>
                            setReservationForm({
                              ...reservationForm,
                              timeSlot: value,
                            })
                          }
                        >
                          <SelectTrigger id="time" className="h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>{TIME_SLOT_OPTIONS}</SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="search-query" className="text-xs">
                        Restaurant Name
                      </Label>
                      <div className="relative">
                        <Input
                          id="search-query"
                          placeholder="e.g., Carbone, Torrisi"
                          value={filters.query}
                          onChange={(e) =>
                            setFilters({ ...filters, query: e.target.value })
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              onSearch(1);
                            }
                          }}
                          className="pr-10 h-9"
                        />
                        <Search className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant={
                          filters.availableOnly ? "secondary" : "outline"
                        }
                        size="sm"
                        className="border text-xs h-8"
                        onClick={() =>
                          setFilters({
                            ...filters,
                            availableOnly: !filters.availableOnly,
                            notReleasedOnly: false,
                          })
                        }
                      >
                        Available Only
                      </Button>
                      <Button
                        variant={
                          filters.notReleasedOnly ? "secondary" : "outline"
                        }
                        size="sm"
                        className="border text-xs h-8"
                        onClick={() =>
                          setFilters({
                            ...filters,
                            notReleasedOnly: !filters.notReleasedOnly,
                            availableOnly: false,
                          })
                        }
                      >
                        Not Released
                      </Button>
                    </div>

                    <Button
                      onClick={() => onSearch(1)}
                      disabled={loading || filters.query.trim() === ""}
                      className="w-full"
                      size="sm"
                    >
                      {loading ? "Searching..." : "Search"}
                    </Button>
                  </TabsContent>

                  {/* Tab: Browse Restaurants */}
                  <TabsContent value="browse" className="space-y-4 mt-0">
                    {/* Reservation Inputs */}
                    <div className="grid grid-cols-3 gap-3">
                      {/* Party Size */}
                      <div className="space-y-1.5">
                        <Label className="text-xs">Party Size</Label>
                        <Select
                          value={reservationForm.partySize}
                          onValueChange={(value) =>
                            setReservationForm({
                              ...reservationForm,
                              partySize: value,
                            })
                          }
                        >
                          <SelectTrigger id="party-size-browse" className="h-9">
                            <SelectValue />
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
                      </div>

                      {/* Date */}
                      <div className="space-y-1.5">
                        <Label className="text-xs">Date</Label>
                        <Popover>
                          <PopoverTrigger asChild>
                            <button
                              className={cn(
                                "flex h-9 w-full items-center justify-start rounded-md border bg-background px-3 py-2 text-sm shadow-xs ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-accent/50 transition-colors",
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
                      </div>

                      {/* Time */}
                      <div className="space-y-1.5">
                        <Label className="text-xs">Time</Label>
                        <Select
                          value={reservationForm.timeSlot}
                          onValueChange={(value) =>
                            setReservationForm({
                              ...reservationForm,
                              timeSlot: value,
                            })
                          }
                        >
                          <SelectTrigger id="time-browse" className="h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>{TIME_SLOT_OPTIONS}</SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      {/* Cuisine Multi-Select */}
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button
                            variant="outline"
                            className="w-full justify-between overflow-hidden h-9 text-xs"
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
                                  className="flex items-center space-x-2 hover:bg-accent rounded-sm"
                                >
                                  <Checkbox
                                    id={`cuisine-browse-${cuisine}`}
                                    checked={filters.cuisines.includes(cuisine)}
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
                                    className="ml-2"
                                  />
                                  <label
                                    htmlFor={`cuisine-browse-${cuisine}`}
                                    className="text-sm p-2 cursor-pointer flex-1 hover:bg-accent rounded-sm"
                                  >
                                    {cuisine}
                                  </label>
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
                            className="w-full justify-between overflow-hidden h-9 text-xs"
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
                                  className="flex items-center space-x-2 hover:bg-accent rounded-sm"
                                >
                                  <Checkbox
                                    id={`price-browse-${price.value}`}
                                    checked={filters.priceRanges.includes(
                                      price.value
                                    )}
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
                                    className="ml-2"
                                  />
                                  <label
                                    htmlFor={`price-browse-${price.value}`}
                                    className="text-sm cursor-pointer flex-1 p-2 hover:bg-accent rounded-sm"
                                  >
                                    {price.label}
                                  </label>
                                </div>
                              )
                            )}
                          </div>
                        </PopoverContent>
                      </Popover>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant={
                          filters.availableOnly ? "secondary" : "outline"
                        }
                        size="sm"
                        className="border text-xs h-8"
                        onClick={() =>
                          setFilters({
                            ...filters,
                            availableOnly: !filters.availableOnly,
                            notReleasedOnly: false,
                          })
                        }
                      >
                        Available Only
                      </Button>
                      <Button
                        variant={
                          filters.notReleasedOnly ? "secondary" : "outline"
                        }
                        size="sm"
                        className="border text-xs h-8"
                        onClick={() =>
                          setFilters({
                            ...filters,
                            notReleasedOnly: !filters.notReleasedOnly,
                            availableOnly: false,
                          })
                        }
                      >
                        Not Released
                      </Button>
                      <Button
                        variant={
                          filters.bookmarkedOnly ? "secondary" : "outline"
                        }
                        size="sm"
                        className="border text-xs h-8"
                        onClick={() =>
                          setFilters({
                            ...filters,
                            bookmarkedOnly: !filters.bookmarkedOnly,
                          })
                        }
                      >
                        <Bookmark className="size-3 mr-1" /> Only
                      </Button>
                    </div>

                    <Button
                      onClick={() => onSearch(1)}
                      disabled={loading || !inputsHaveChanged}
                      className="w-full"
                      size="sm"
                    >
                      {loading ? "Searching..." : "Search Restaurants"}
                    </Button>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            {/* Search Results */}
            <div>
              {loading && (
                <div className="text-center py-8 text-muted-foreground">
                  Loading results...
                </div>
              )}

              {!loading && hasSearched && searchResults.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No restaurants found. Try a different search.
                  {currentPage > 1 && (
                    <div className="mt-2">
                      <Button variant="outline" onClick={() => onPageChange(1)}>
                        Go back to first page
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {!loading && searchResults.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Found {pagination?.total || searchResults.length} restaurant
                    {(pagination?.total || searchResults.length) !== 1
                      ? "s"
                      : ""}
                    {pagination && (currentPage > 1 || hasNextPage) && (
                      <span> (Page {currentPage})</span>
                    )}
                  </p>
                  <div className="space-y-1">
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
                  </div>
                </div>
              )}

              {!loading && !hasSearched && (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center space-y-3">
                    <Search className="size-12 mx-auto text-muted-foreground" />
                    <h3 className="text-lg font-medium">
                      Search for Restaurants
                    </h3>
                    <p className="text-sm text-muted-foreground max-w-[280px]">
                      Enter a restaurant name and customize your filters to find
                      the perfect dining experience in NYC
                    </p>
                  </div>
                </div>
              )}
            </div>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* Pagination Footer */}
      {!loading &&
        searchResults.length > 0 &&
        pagination &&
        (currentPage > 1 || hasNextPage) && (
          <SidebarFooter className="border-t p-2">
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (currentPage > 1) {
                        onPageChange(currentPage - 1);
                      }
                    }}
                    className={
                      currentPage === 1 ? "pointer-events-none opacity-50" : ""
                    }
                  />
                </PaginationItem>

                <PaginationItem>
                  <PaginationLink
                    href="#"
                    onClick={(e) => e.preventDefault()}
                    isActive={true}
                  >
                    {currentPage}
                  </PaginationLink>
                </PaginationItem>

                {hasNextPage && (
                  <PaginationItem>
                    <PaginationEllipsis />
                  </PaginationItem>
                )}

                <PaginationItem>
                  <PaginationNext
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (hasNextPage) {
                        onPageChange(currentPage + 1);
                      }
                    }}
                    className={
                      !hasNextPage ? "pointer-events-none opacity-50" : ""
                    }
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </SidebarFooter>
        )}
    </Sidebar>
  );
}
