import { createContext, useContext, useState, type ReactNode } from 'react'
import type { SearchResult, GeminiSearchResponse } from '@/lib/api'

export interface ReservationFormState {
  partySize: string
  date: Date | undefined
  timeSlot: string
  windowHours: string
  seatingType: string
  dropTimeSlot: string
  dropDate: Date | undefined
}

interface VenueContextType {
  selectedVenueId: string
  setSelectedVenueId: (id: string) => void
  searchResults: SearchResult[]
  setSearchResults: (results: SearchResult[]) => void
  searchQuery: string
  setSearchQuery: (query: string) => void
  reservationForm: ReservationFormState
  setReservationForm: (form: ReservationFormState) => void
  aiSummaryCache: Record<string, GeminiSearchResponse>
  setAiSummaryCache: (cache: Record<string, GeminiSearchResponse>) => void
}

const VenueContext = createContext<VenueContextType | undefined>(undefined)

export function VenueProvider({ children }: { children: ReactNode }) {
  const [selectedVenueId, setSelectedVenueId] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [reservationForm, setReservationForm] = useState<ReservationFormState>({
    partySize: '2',
    date: undefined,
    timeSlot: '19:0', // Default to 7:00 PM
    windowHours: '1',
    seatingType: 'any',
    dropTimeSlot: '9:0', // Default to 9:00 AM
    dropDate: undefined,
  })
  const [aiSummaryCache, setAiSummaryCache] = useState<Record<string, GeminiSearchResponse>>({})

  return (
    <VenueContext.Provider
      value={{
        selectedVenueId,
        setSelectedVenueId,
        searchResults,
        setSearchResults,
        searchQuery,
        setSearchQuery,
        reservationForm,
        setReservationForm,
        aiSummaryCache,
        setAiSummaryCache
      }}
    >
      {children}
    </VenueContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useVenue() {
  const context = useContext(VenueContext)
  if (!context) {
    throw new Error('useVenue must be used within a VenueProvider')
  }
  return context
}
