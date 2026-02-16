import * as Sentry from "@sentry/react";
import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Search, LogIn } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useVenue } from "@/contexts/VenueContext";
import { searchRestaurants } from "@/lib/api";
import { SearchResultItem } from "@/components/SearchResultItem";
import { useAuth } from "@/contexts/AuthContext";
import { useAtom, useAtomValue } from "jotai";
import { cityAtom } from "@/atoms/cityAtom";
import { isAuthLoadingAtom, isOnboardedAtom } from "@/atoms/authAtoms";
import { LoaderSpinner } from "@/components/ui/loader-spinner";

interface SearchBarProps {
  className?: string;
  inputClassName?: string;
  placeholderText?: string;
}

export function SearchBar({
  className,
  inputClassName,
  placeholderText = "e.g., Carbone, Torrisi",
}: SearchBarProps) {
  const navigate = useNavigate();
  const { searchResults, setSearchResults, searchQuery, setSearchQuery } =
    useVenue();
  const [loading, setLoading] = useState(false);
  const [searchPopoverOpen, setSearchPopoverOpen] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const [, setShowLoginPrompt] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const currentQueryRef = useRef<string>("");
  const auth = useAuth();
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isAuthenticated = !!auth.currentUser;
  const isAuthLoading = useAtomValue(isAuthLoadingAtom);
  const isOnboarded = useAtomValue(isOnboardedAtom);
  const [selectedCity] = useAtom(cityAtom);

  // Prevent body scroll when popover is open
  useEffect(() => {
    if (searchPopoverOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [searchPopoverOpen]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Debounced search function
  const performSearch = useCallback(
    async (query: string) => {
      const querySnapshot = query;
      setLoading(true);
      if (inputFocused) {
        setSearchPopoverOpen(true);
      }

      try {
        // Create SearchFilter
        const searchFilter = {
          query,
        };

        const user = auth.currentUser;
        const results = (
          await searchRestaurants(user!.uid, searchFilter, selectedCity)
        ).results;

        // Check if this query is still current
        if (currentQueryRef.current !== querySnapshot) {
          return; // Ignore results from old queries
        }

        // Don't fetch photos here - images will load lazily from the imageUrl
        // that's already in the search results from the backend
        setSearchResults(results);
        if (inputFocused && (results.length > 0 || !query.trim())) {
          setSearchPopoverOpen(true);
        }
      } catch (err) {
        console.error("Search error:", err);
        Sentry.captureException(err);
        if (currentQueryRef.current === querySnapshot) {
          setSearchPopoverOpen(false);
        }
      } finally {
        if (currentQueryRef.current === querySnapshot) {
          setLoading(false);
        }
      }
    },
    [auth.currentUser, inputFocused, setSearchResults],
  );

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    currentQueryRef.current = value;

    // Clear existing debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!value.trim()) {
      setSearchResults([]);
      if (inputFocused) {
        setSearchPopoverOpen(true);
      }
      return;
    }

    // Debounce search by 300ms
    debounceTimerRef.current = setTimeout(() => {
      performSearch(value);
    }, 300);
  };

  const handleSelectVenue = (venueId: string) => {
    setSearchPopoverOpen(false);
    setInputFocused(false);
    navigate(`/venue?id=${venueId}`);
  };

  const handleViewAll = () => {
    setSearchPopoverOpen(false);
    setInputFocused(false);
    navigate("/search");
  };

  // If still loading credentials, show loading overlay
  if (isAuthLoading) {
    return (
      <div
        className={`relative group ${className}`}
        style={{ position: "relative", zIndex: 10001 }}
      >
        {/* Loading overlay */}
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-muted/95 dark:bg-muted/95 rounded-md border border-border">
          <div className="flex items-center gap-2 text-muted-foreground">
            <LoaderSpinner size="sm" />
            <span>Loading credentials...</span>
          </div>
        </div>

        {/* Disabled input */}
        <Input
          placeholder={placeholderText}
          disabled
          className={`shadow-md bg-background ${inputClassName ?? ""}`}
        />
        <Search className="absolute right-6 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
      </div>
    );
  }

  // If not authenticated, show a disabled search bar with login prompt on hover/click
  if (!isAuthenticated) {
    return (
      <div
        className={`relative group ${className}`}
        style={{ position: "relative", zIndex: 10001 }}
      >
        {/* Login prompt overlay - shows on hover */}
        <div
          className="absolute inset-0 z-10 flex items-center justify-center bg-red-50/95 dark:bg-red-950/95 rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 cursor-pointer border border-red-200 dark:border-red-800"
          onClick={() => navigate("/login")}
        >
          <div className="flex items-center gap-2 text-red-700 dark:text-red-300 font-medium">
            <LogIn className="size-4" />
            <span>Log in to search</span>
          </div>
        </div>

        {/* Disabled input */}
        <Input
          placeholder={placeholderText}
          disabled
          onClick={() => {
            setShowLoginPrompt(true);
            navigate("/login");
          }}
          className={`shadow-md bg-background cursor-pointer ${inputClassName}`}
        />
        <Search className="absolute right-6 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
      </div>
    );
  }

  // If authenticated but not onboarded, show "Connect your Resy account to search"
  if (isAuthenticated && !isOnboarded) {
    return (
      <div
        className={`relative group ${className}`}
        style={{ position: "relative", zIndex: 10001 }}
      >
        {/* Connect Resy prompt overlay - shows on hover */}
        <div
          className="absolute inset-0 z-10 flex items-center justify-center bg-red-50/95 dark:bg-red-950/95 rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 cursor-pointer border border-red-200 dark:border-red-800"
          onClick={() => navigate("/connect-resy")}
        >
          <div className="flex items-center gap-2 text-red-700 dark:text-red-300 font-medium">
            <LogIn className="size-4" />
            <span>Connect your Resy account to search</span>
          </div>
        </div>

        {/* Disabled input */}
        <Input
          placeholder={placeholderText}
          disabled
          onClick={() => {
            navigate("/connect-resy");
          }}
          className={`shadow-md bg-background cursor-pointer ${inputClassName}`}
        />
        <Search className="absolute right-6 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
      </div>
    );
  }

  return (
    <>
      {/* Backdrop overlay when searching - z-index must be above header (9998) and footer (999) */}
      {searchPopoverOpen && (
        <div
          className="fixed inset-0 bg-black/50"
          style={{ zIndex: 10000 }}
          onClick={() => {
            setSearchPopoverOpen(false);
            setInputFocused(false);
          }}
        />
      )}

      <Popover open={searchPopoverOpen} onOpenChange={setSearchPopoverOpen}>
        <PopoverTrigger asChild>
          <div
            className={`cursor-text! transition-all duration-200 ease-out ${searchPopoverOpen ? "" : "border shadow-md"} ${className}`}
            style={{ position: "relative", zIndex: 10001 }}
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            <Input
              ref={inputRef}
              placeholder={placeholderText}
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              onFocus={() => {
                setInputFocused(true);
                setSearchPopoverOpen(true);
              }}
              onBlur={() => {
                setTimeout(() => {
                  setInputFocused(false);
                }, 200);
              }}
              onClick={(e) => {
                e.stopPropagation();
              }}
              onMouseDown={(e) => {
                e.stopPropagation();
              }}
              autoComplete="off"
              className={`bg-background transition-all duration-200 ease-out ${searchPopoverOpen ? "border-0 shadow-none focus-visible:ring-0 focus-visible:border-transparent" : "shadow-sm"} ${inputClassName}`}
            />
            <Search className="absolute right-6 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
            <div
              className={`absolute -left-px -right-px top-full -translate-y-7 -z-1 h-10 bg-background transition-all duration-200 ease-out ${searchPopoverOpen ? "opacity-100" : "opacity-0"}`}
            />
          </div>
        </PopoverTrigger>
        <PopoverContent
          className={`w-(--radix-popover-trigger-width) ${searchPopoverOpen && searchResults.length === 0 && "rounded-b-3xl"} rounded-t-none p-0 pb-1 border-0`}
          style={{ zIndex: 10002 }}
          align="start"
          sideOffset={0}
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          {/* Horizontal divider between search bar and content */}
          <div className="h-px bg-border mx-4" />
          {loading ? (
            <div className="p-4 text-center text-sm text-muted-foreground rounded-b-full">
              Loading results...
            </div>
          ) : searchResults.length > 0 ? (
            <div className="max-h-[500px] overflow-y-auto">
              {searchResults.slice(0, 8).map((result) => (
                <SearchResultItem
                  key={result.id}
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
                  onCardClick={handleSelectVenue}
                  imageSize="small"
                />
              ))}
              {searchResults.length > 8 && (
                <div className="p-2 border-t">
                  <Button
                    variant="ghost"
                    className="w-full"
                    onClick={handleViewAll}
                  >
                    See all {searchResults.length} results
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 rounded-b-full">
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={handleViewAll}
              >
                <Search className="mr-2 size-4" />
                View all restaurants
              </Button>
            </div>
          )}
        </PopoverContent>
      </Popover>
    </>
  );
}
