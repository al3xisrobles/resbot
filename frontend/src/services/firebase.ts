import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getDatabase, ref, get, set } from "firebase/database";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import type { TrendingRestaurant } from "@/lib/api";

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBsxxRvxe_UB9VGgibgGMzWpunpo0Ji5Hc",
  authDomain: "resybot-bd2db.firebaseapp.com",
  projectId: "resybot-bd2db",
  storageBucket: "resybot-bd2db.firebasestorage.app",
  messagingSenderId: "782094781658",
  appId: "1:782094781658:web:a5935d09518547971ea9e3",
  measurementId: "G-JVN6BECKSE",
  databaseURL: "https://resybot-bd2db-default-rtdb.firebaseio.com"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const database = getDatabase(app);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

console.log('[Firebase] Initialized with config:', {
  projectId: firebaseConfig.projectId,
  databaseURL: firebaseConfig.databaseURL
});
console.log('[Firebase] Database instance:', database);

export interface VenueCacheData {
  // Venue basic info
  venueName?: string;
  venueType?: string;
  address?: string;
  neighborhood?: string;
  priceRange?: number;
  rating?: number;

  // Links
  googleMapsLink?: string;
  resyLink?: string;
  photoUrl?: string;  // Kept for backwards compatibility
  photoUrls?: string[];  // Array of photo URLs

  // AI insights
  aiInsights?: string;

  // Metadata
  lastUpdated: number;
}

/**
 * Check if venue data exists in cache
 */
export async function hasVenueCache(venueId: string): Promise<boolean> {
  try {
    const venueRef = ref(database, `venues/${venueId}`);
    const snapshot = await get(venueRef);
    return snapshot.exists();
  } catch (error) {
    console.error('Error checking venue cache:', error);
    return false;
  }
}

/**
 * Get cached venue data
 */
export async function getVenueCache(venueId: string): Promise<VenueCacheData | null> {
  try {
    const path = `venues/${venueId}`;
    console.log('[Firebase] Getting cache for venue:', venueId);
    console.log('[Firebase] Database path:', path);
    console.log('[Firebase] Database URL:', database.app.options.databaseURL);

    const venueRef = ref(database, path);
    const snapshot = await get(venueRef);

    console.log('[Firebase] Snapshot exists:', snapshot.exists());
    if (snapshot.exists()) {
      const data = snapshot.val() as VenueCacheData;
      console.log('[Firebase] Cache hit! Data:', data);
      return data;
    }
    console.log('[Firebase] Cache miss - no data found');
    return null;
  } catch (error) {
    console.error('[Firebase] Error getting venue cache:', error);
    console.error('[Firebase] Error details:', {
      message: error instanceof Error ? error.message : 'Unknown error',
      venueId,
      path: `venues/${venueId}`
    });
    return null;
  }
}

/**
 * Save venue data to cache
 */
export async function saveVenueCache(venueId: string, data: Partial<VenueCacheData>): Promise<boolean> {
  try {
    const path = `venues/${venueId}`;
    console.log('[Firebase] Saving cache for venue:', venueId);
    console.log('[Firebase] Database path:', path);
    console.log('[Firebase] Data to save:', data);

    const venueRef = ref(database, path);

    // Get existing data to merge with new data
    const snapshot = await get(venueRef);
    const existingData = snapshot.exists() ? snapshot.val() : {};

    // Merge and save
    const updatedData = {
      ...existingData,
      ...data,
      lastUpdated: Date.now()
    };

    console.log('[Firebase] Merged data:', updatedData);
    await set(venueRef, updatedData);
    console.log('[Firebase] Successfully saved cache');
    return true;
  } catch (error) {
    console.error('[Firebase] Error saving venue cache:', error);
    console.error('[Firebase] Error details:', {
      message: error instanceof Error ? error.message : 'Unknown error',
      venueId,
      path: `venues/${venueId}`,
      data
    });
    return false;
  }
}

/**
 * Update only AI insights for a venue
 */
export async function saveAiInsights(venueId: string, aiInsights: string): Promise<boolean> {
  return saveVenueCache(venueId, { aiInsights });
}

export interface TrendingRestaurantsCacheData {
  restaurants: TrendingRestaurant[];
  lastUpdated: number;
}

/**
 * Get cached trending restaurants
 * @param maxAgeMs - Maximum age of cache in milliseconds (default: 7 days)
 * @returns Cached data if valid, null otherwise
 */
export async function getTrendingRestaurantsCache(maxAgeMs: number = 7 * 24 * 60 * 60 * 1000): Promise<TrendingRestaurant[] | null> {
  try {
    const path = 'trending/restaurants';
    console.log('[Firebase] Getting trending restaurants cache');

    const cacheRef = ref(database, path);
    const snapshot = await get(cacheRef);

    if (snapshot.exists()) {
      const data = snapshot.val() as TrendingRestaurantsCacheData;
      const age = Date.now() - data.lastUpdated;

      console.log(`[Firebase] Cache found. Age: ${Math.floor(age / 1000 / 60)} minutes`);

      if (age < maxAgeMs) {
        console.log('[Firebase] Cache is still valid');
        return data.restaurants;
      } else {
        console.log('[Firebase] Cache expired');
        return null;
      }
    }

    console.log('[Firebase] No cache found');
    return null;
  } catch (error) {
    console.error('[Firebase] Error getting trending restaurants cache:', error);
    return null;
  }
}

/**
 * Save trending restaurants to cache
 */
export async function saveTrendingRestaurantsCache(restaurants: TrendingRestaurant[]): Promise<boolean> {
  try {
    const path = 'trending/restaurants';
    console.log('[Firebase] Saving trending restaurants cache');

    const cacheRef = ref(database, path);
    const cacheData: TrendingRestaurantsCacheData = {
      restaurants,
      lastUpdated: Date.now()
    };

    await set(cacheRef, cacheData);
    console.log('[Firebase] Successfully saved trending restaurants cache');
    return true;
  } catch (error) {
    console.error('[Firebase] Error saving trending restaurants cache:', error);
    return false;
  }
}

/**
 * Get cached top-rated restaurants
 * @param maxAgeMs - Maximum age of cache in milliseconds (default: 7 days)
 * @returns Cached data if valid, null otherwise
 */
export async function getTopRatedRestaurantsCache(maxAgeMs: number = 7 * 24 * 60 * 60 * 1000): Promise<TrendingRestaurant[] | null> {
  try {
    const path = 'topRated/restaurants';
    console.log('[Firebase] Getting top-rated restaurants cache');

    const cacheRef = ref(database, path);
    const snapshot = await get(cacheRef);

    if (snapshot.exists()) {
      const data = snapshot.val() as TrendingRestaurantsCacheData;
      const age = Date.now() - data.lastUpdated;

      console.log(`[Firebase] Cache found. Age: ${Math.floor(age / 1000 / 60)} minutes`);

      if (age < maxAgeMs) {
        console.log('[Firebase] Cache is still valid');
        return data.restaurants;
      } else {
        console.log('[Firebase] Cache expired');
        return null;
      }
    }

    console.log('[Firebase] No cache found');
    return null;
  } catch (error) {
    console.error('[Firebase] Error getting top-rated restaurants cache:', error);
    return null;
  }
}

/**
 * Save top-rated restaurants to cache
 */
export async function saveTopRatedRestaurantsCache(restaurants: TrendingRestaurant[]): Promise<boolean> {
  try {
    const path = 'topRated/restaurants';
    console.log('[Firebase] Saving top-rated restaurants cache');

    const cacheRef = ref(database, path);
    const cacheData: TrendingRestaurantsCacheData = {
      restaurants,
      lastUpdated: Date.now()
    };

    await set(cacheRef, cacheData);
    console.log('[Firebase] Successfully saved top-rated restaurants cache');
    return true;
  } catch (error) {
    console.error('[Firebase] Error saving top-rated restaurants cache:', error);
    return false;
  }
}

export { database, analytics, auth, googleProvider };
