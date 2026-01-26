import { useState } from "react";
import { Search, AlertCircle, MapPin, ChevronRight } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { searchRestaurants } from "@/lib/api";
import { useVenue } from "@/contexts/VenueContext";
import { useAuth } from "@/contexts/AuthContext";
import { useAtom } from "jotai";
import { cityAtom } from "@/atoms/cityAtom";

export function SearchTab({
  onTabChange,
}: {
  onTabChange: (tab: string) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const auth = useAuth();
  const [selectedCity] = useAtom(cityAtom);
  const {
    setSelectedVenueId,
    searchResults,
    setSearchResults,
    searchQuery,
    setSearchQuery,
  } = useVenue();

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError("Please enter a restaurant name");
      return;
    }

    setLoading(true);
    setError(null);
    setSearchResults([]);

    try {
      const user = auth.currentUser;
      const response = await searchRestaurants(user!.uid, {
        query: searchQuery,
      }, selectedCity);
      setSearchResults(response.results);

      if (response.results.length === 0) {
        setError("No restaurants found matching your search");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to search restaurants"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSelectVenue = (venueId: string) => {
    setSelectedVenueId(venueId);
    onTabChange("reserve");
  };

  return (
    <Card className="px-10 py-16">
      <CardHeader>
        <CardTitle>Restaurant Search</CardTitle>
        <CardDescription>
          Search for restaurants by name to make a reservation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Error Messages */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex gap-4">
          <div className="flex-1">
            <Input
              id="search-query"
              placeholder="e.g., Carbone, Torrisi"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
          </div>
          <div className="flex items-end">
            <Button onClick={handleSearch} disabled={loading || !searchQuery}>
              <Search className="mr-2 size-4" />
              {loading ? "Searching..." : "Search"}
            </Button>
          </div>
        </div>

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="mt-6 space-y-3">
            <h3 className="text-sm font-semibold text-foreground">
              Search Results
            </h3>
            <div className="space-y-2">
              {searchResults.map((result) => (
                <button
                  key={result.id}
                  onClick={() => handleSelectVenue(result.id)}
                  className="w-full text-left p-4 rounded-lg border border-border hover:border-primary hover:bg-accent/50 transition-all cursor-pointer group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {result.name}
                        </h4>
                        {result.price_range > 0 && (
                          <span className="text-sm text-muted-foreground">
                            {"$".repeat(result.price_range)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <MapPin className="size-3" />
                        <span>
                          {[result.neighborhood, result.locality, result.region]
                            .filter(Boolean)
                            .join(", ")}
                        </span>
                      </div>
                      {result.type && result.type != "N/A" && (
                        <p className="text-sm text-muted-foreground">
                          {result.type}
                        </p>
                      )}
                    </div>
                    <ChevronRight className="size-5 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
