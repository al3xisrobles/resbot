import { useState, useEffect } from "react";
import { searchRestaurant, getVenueLinks } from "@/lib/api";
import type { VenueLinksResponse } from "@/lib/interfaces";
import { getVenueCache, saveVenueCache } from "@/services/firebase";
import { useAuth } from "@/contexts/AuthContext";
import type { VenueData, VenueLinks } from "../lib/types";

export function useVenueData(venueId: string | null) {
  const auth = useAuth();
  const [venueData, setVenueData] = useState<VenueData | null>(null);
  const [loadingVenue, setLoadingVenue] = useState(true);
  const [venueError, setVenueError] = useState<string | null>(null);
  const [venueLinks, setVenueLinks] = useState<VenueLinks | null>(null);
  const [loadingLinks, setLoadingLinks] = useState(false);

  useEffect(() => {
    if (!venueId) {
      setVenueError("No venue ID provided");
      setLoadingVenue(false);
      return;
    }

    const fetchVenueLinksAndData = async () => {
      try {
        setLoadingVenue(true);
        setLoadingLinks(true);

        // Check Firebase cache first
        const cachedData = await getVenueCache(venueId);

        // Check if we have both links AND complete venue data in cache
        const hasCompleteCache =
          cachedData?.googleMapsLink !== undefined &&
          cachedData?.resyLink !== undefined &&
          cachedData?.venueName &&
          cachedData?.venueType;

        // Check if photoUrls is empty in cache (invalid cache - need to refetch)
        const hasEmptyPhotoUrls =
          !cachedData?.photoUrls ||
          (Array.isArray(cachedData.photoUrls) && cachedData.photoUrls.length === 0);

        // Check if cache is missing the description field (cached before we added it)
        // If 'description' key doesn't exist in the cache object, it's stale
        const isMissingDescriptionField = cachedData && !('description' in cachedData);

        if (hasCompleteCache && !hasEmptyPhotoUrls && !isMissingDescriptionField) {
          // We have cached links and venue data with photos, use them
          setVenueLinks({
            googleMaps: cachedData.googleMapsLink || null,
            resy: cachedData.resyLink || null,
          });

          // Use cached venue data
          setVenueData({
            name: cachedData.venueName || "",
            venue_id: venueId,
            type: cachedData.venueType || "",
            address: cachedData.address || "",
            neighborhood: cachedData.neighborhood || "",
            price_range: cachedData.priceRange || 0,
            rating: cachedData.rating ?? null,
            photoUrls: cachedData.photoUrls || [],
            description: cachedData.description,
          });
          setLoadingVenue(false);
        } else {
          // No cache, or cache has empty photoUrls - fetch from API
          const user = auth.currentUser;

          // Fetch venue data first to get photoUrls
          const venueDataResponse = await searchRestaurant(user!.uid, venueId);

          // Fetch venue links
          const response: VenueLinksResponse = await getVenueLinks(
            user!.uid,
            venueId
          );
          setVenueLinks(response.links);

          // Set venue data with photoUrls from the API response
          setVenueData({
            name: venueDataResponse.name,
            venue_id: venueId,
            type: venueDataResponse.type,
            address: venueDataResponse.address,
            neighborhood: venueDataResponse.neighborhood,
            price_range: venueDataResponse.price_range,
            rating: venueDataResponse.rating,
            photoUrls: venueDataResponse.photoUrls || [],
            description: venueDataResponse.description,
          });

          // Save links and venue data to Firebase cache
          await saveVenueCache(venueId, {
            googleMapsLink: response.links.googleMaps || undefined,
            resyLink: response.links.resy || undefined,
            venueName: venueDataResponse.name,
            venueType: venueDataResponse.type,
            address: venueDataResponse.address,
            neighborhood: venueDataResponse.neighborhood,
            priceRange: venueDataResponse.price_range,
            rating: venueDataResponse.rating ?? undefined,
            photoUrls: venueDataResponse.photoUrls || undefined,
            description: venueDataResponse.description,
          });
          setLoadingVenue(false);
        }
      } catch (err) {
        setVenueError(
          err instanceof Error ? err.message : "Failed to load venue"
        );
      } finally {
        setLoadingLinks(false);
        setLoadingVenue(false);
      }
    };

    fetchVenueLinksAndData();
  }, [venueId, auth.currentUser]);

  return {
    venueData,
    loadingVenue,
    venueError,
    venueLinks,
    loadingLinks,
  };
}
