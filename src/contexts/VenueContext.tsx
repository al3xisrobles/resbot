import { createContext, useContext, useState, type ReactNode, type Dispatch, type SetStateAction } from "react";
import type { SearchResult, GeminiSearchResponse } from "@/lib/interfaces";

export interface ReservationFormState {
  partySize: string;
  date: Date | undefined;
  timeSlot: string;
  windowHours: string;
  seatingType: string;
  dropTimeSlot: string;
  dropDate: Date | undefined;
}

interface VenueContextType {
  selectedVenueId: string;
  setSelectedVenueId: (id: string) => void;
  searchResults: SearchResult[];
  setSearchResults: (results: SearchResult[]) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  aiSummaryCache: Record<string, GeminiSearchResponse>;
  setAiSummaryCache: Dispatch<SetStateAction<Record<string, GeminiSearchResponse>>>;
}

const VenueContext = createContext<VenueContextType | undefined>(undefined);

export function VenueProvider({ children }: { children: ReactNode }) {
  const [selectedVenueId, setSelectedVenueId] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [aiSummaryCache, setAiSummaryCache] = useState<
    Record<string, GeminiSearchResponse>
  >({});

  return (
    <VenueContext.Provider
      value={{
        selectedVenueId,
        setSelectedVenueId,
        searchResults,
        setSearchResults,
        searchQuery,
        setSearchQuery,
        aiSummaryCache,
        setAiSummaryCache,
      }}
    >
      {children}
    </VenueContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useVenue() {
  const context = useContext(VenueContext);
  if (!context) {
    throw new Error("useVenue must be used within a VenueProvider");
  }
  return context;
}
