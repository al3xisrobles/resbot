import { RestaurantSearchContainer } from "@/features/restaurant-search/components/RestaurantSearchContainer";

export function SearchPage() {
  return <RestaurantSearchContainer />;
}

// Re-export types for convenience
export type { SearchFilters } from "@/features/restaurant-search/lib/types";
