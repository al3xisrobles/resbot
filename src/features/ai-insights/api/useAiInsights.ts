import { useState, useEffect, useRef, useCallback } from "react";
import { getGeminiSearch } from "@/lib/api";
import { getVenueCache, saveAiInsights } from "@/services/firebase";
import { useAuth } from "@/contexts/AuthContext";
import { useVenue } from "@/contexts/VenueContext";
import type { GeminiSearchResponse } from "../lib/types";

export function useAiInsights(venueId: string | null, venueName: string | null) {
  const auth = useAuth();
  const { aiSummaryCache, setAiSummaryCache } = useVenue();
  const [aiSummary, setAiSummary] = useState<GeminiSearchResponse | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiLastUpdated, setAiLastUpdated] = useState<number | null>(null);

  // Track current venueId to prevent stale updates from previous requests
  const currentVenueIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!venueName || !venueId) return;

    // Update ref to track current venue
    currentVenueIdRef.current = venueId;

    // Reset state immediately when venue changes to prevent showing stale data
    setAiSummary(null);
    setAiError(null);
    setAiLastUpdated(null);

    // Check in-memory cache first (access directly without dependency)
    const cachedSummary = aiSummaryCache[venueId];
    if (cachedSummary) {
      setAiSummary(cachedSummary);
      setLoadingAi(false);
      return;
    }

    // Track if this effect instance is still active
    let isCancelled = false;

    // If not in memory cache, check Firebase and fetch from API if needed
    const fetchAiSummary = async () => {
      // Bail out if cancelled or venue changed during fetch
      if (isCancelled || currentVenueIdRef.current !== venueId) return;

      try {
        setLoadingAi(true);

        // Check Firebase cache
        const cachedData = await getVenueCache(venueId);

        // Bail out if cancelled or venue changed during fetch
        if (isCancelled || currentVenueIdRef.current !== venueId) return;

        if (cachedData?.aiInsights) {
          // Parse the cached AI insights back to GeminiSearchResponse
          const cachedFirebaseSummary = JSON.parse(
            cachedData.aiInsights
          ) as GeminiSearchResponse;
          setAiSummary(cachedFirebaseSummary);
          setAiLastUpdated(cachedData.lastUpdated);

          // Store in memory cache too
          setAiSummaryCache((prev) => ({
            ...prev,
            [venueId]: cachedFirebaseSummary,
          }));
        } else {
          // Not in Firebase, fetch from API
          // Capture current values to ensure we use the correct venue
          const currentVenueId = venueId;
          const currentVenueName = venueName;

          const user = auth.currentUser;
          const summary = await getGeminiSearch(
            user!.uid,
            currentVenueName,
            currentVenueId
          );

          // Bail out if cancelled or venue changed during fetch
          if (isCancelled || currentVenueIdRef.current !== currentVenueId) return;

          setAiSummary(summary);
          const now = Date.now();
          setAiLastUpdated(now);

          // Store in both caches
          setAiSummaryCache((prev) => ({
            ...prev,
            [currentVenueId]: summary,
          }));

          // Save to Firebase
          await saveAiInsights(currentVenueId, JSON.stringify(summary));
        }
      } catch (err) {
        // Only set error if this is still the current venue and not cancelled
        if (!isCancelled && currentVenueIdRef.current === venueId) {
          setAiError(
            err instanceof Error ? err.message : "Failed to load AI summary"
          );
        }
      } finally {
        // Only update loading state if this is still the current venue and not cancelled
        if (!isCancelled && currentVenueIdRef.current === venueId) {
          setLoadingAi(false);
        }
      }
    };

    fetchAiSummary();

    // Cleanup: mark this effect as cancelled when it re-runs or unmounts
    return () => {
      isCancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [venueId, venueName]); // Only re-run when venue changes, not when cache updates

  const refreshAiSummary = useCallback(async () => {
    if (!venueName || !venueId) return;

    // Capture current values at the start
    const currentVenueId = venueId;
    const currentVenueName = venueName;

    try {
      setLoadingAi(true);
      setAiError(null);
      const user = auth.currentUser;
      const summary = await getGeminiSearch(
        user!.uid,
        currentVenueName,
        currentVenueId
      );

      // Only update if still on the same venue
      if (currentVenueIdRef.current !== currentVenueId) return;

      setAiSummary(summary);
      const now = Date.now();
      setAiLastUpdated(now);

      // Update both caches using functional update
      setAiSummaryCache((prev) => ({
        ...prev,
        [currentVenueId]: summary,
      }));

      // Update Firebase cache
      await saveAiInsights(currentVenueId, JSON.stringify(summary));
    } catch (err) {
      if (currentVenueIdRef.current === currentVenueId) {
        setAiError(
          err instanceof Error ? err.message : "Failed to load AI summary"
        );
      }
    } finally {
      if (currentVenueIdRef.current === currentVenueId) {
        setLoadingAi(false);
      }
    }
  }, [venueName, venueId, auth.currentUser, setAiSummaryCache]);

  return {
    aiSummary,
    loadingAi,
    aiError,
    aiLastUpdated,
    refreshAiSummary,
  };
}
