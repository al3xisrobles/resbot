import { initializeApp } from "firebase/app";
import {
  getAnalytics,
  isSupported as isAnalyticsSupported,
} from "firebase/analytics";
import {
  getFirestore,
  connectFirestoreEmulator,
  doc,
  getDoc,
  setDoc,
  collection,
  getDocs,
  deleteDoc,
  Timestamp,
  where,
  query,
  orderBy,
} from "firebase/firestore";
import {
  getAuth,
  GoogleAuthProvider,
  connectAuthEmulator,
} from "firebase/auth";
import { getFunctions, connectFunctionsEmulator } from "firebase/functions";
import { getStorage, connectStorageEmulator } from "firebase/storage";
import type { TrendingRestaurant } from "@/lib/interfaces";

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBsxxRvxe_UB9VGgibgGMzWpunpo0Ji5Hc",
  authDomain: "resybot-bd2db.firebaseapp.com",
  projectId: "resybot-bd2db",
  storageBucket: "resybot-bd2db.firebasestorage.app",
  messagingSenderId: "782094781658",
  appId: "1:782094781658:web:a5935d09518547971ea9e3",
  measurementId: "G-JVN6BECKSE",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

let analytics: ReturnType<typeof getAnalytics> | null = null;
if (typeof window !== "undefined") {
  isAnalyticsSupported().then((supported) => {
    if (supported) {
      analytics = getAnalytics(app);
    }
  });
}

const db = getFirestore(app);
const auth = getAuth(app);
const functions = getFunctions(app);
const storage = getStorage(app);
const googleProvider = new GoogleAuthProvider();

// ---- EMULATOR WIRING ----

// Auto-enable on localhost
const useEmulators =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

let CLOUD_FUNCTIONS_BASE: string;

if (useEmulators) {
  console.log("[Firebase] Connecting to emulators…");
  connectFirestoreEmulator(db, "127.0.0.1", 8080);
  connectAuthEmulator(auth, "http://127.0.0.1:9099");
  connectFunctionsEmulator(functions, "127.0.0.1", 5001);
  connectStorageEmulator(storage, "127.0.0.1", 9199);

  console.log("[Firebase] Connected to emulators");
  CLOUD_FUNCTIONS_BASE = "http://127.0.0.1:5001/resybot-bd2db/us-central1";
} else {
  // Prod Cloud Functions base
  console.log("[Firebase] Using production Firebase services");
  CLOUD_FUNCTIONS_BASE = "https://us-central1-resybot-bd2db.cloudfunctions.net";
}

console.log("[Firebase] Initialized with config:", {
  projectId: firebaseConfig.projectId,
});
console.log("[Firebase] Firestore instance:", db);

const CREATE_SNIPE_URL = "https://create-snipe-hypomglm7a-uc.a.run.app";

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
  photoUrl?: string; // Kept for backwards compatibility
  photoUrls?: string[]; // Array of photo URLs

  // AI insights
  aiInsights?: string;

  // Metadata
  lastUpdated: number;
}

export interface BookmarkData {
  venueId: string;
  venueName: string;
  venueType?: string;
  neighborhood?: string;
  priceRange?: number;
  imageUrl?: string;
  bookmarkedAt: number;
}

/**
 * Check if venue data exists in cache
 */
export async function hasVenueCache(venueId: string): Promise<boolean> {
  try {
    const venueDoc = doc(db, "venues", venueId);
    const snapshot = await getDoc(venueDoc);
    return snapshot.exists();
  } catch (error) {
    console.error("Error checking venue cache:", error);
    return false;
  }
}

/**
 * Get cached venue data
 */
export async function getVenueCache(
  venueId: string
): Promise<VenueCacheData | null> {
  try {
    console.log("[Firebase] Getting cache for venue:", venueId);

    const venueDoc = doc(db, "venues", venueId);
    const snapshot = await getDoc(venueDoc);

    console.log("[Firebase] Snapshot exists:", snapshot.exists());
    if (snapshot.exists()) {
      const data = snapshot.data() as VenueCacheData;
      console.log("[Firebase] Cache hit! Data:", data);
      return data;
    }
    console.log("[Firebase] Cache miss - no data found");
    return null;
  } catch (error) {
    console.error("[Firebase] Error getting venue cache:", error);
    console.error("[Firebase] Error details:", {
      message: error instanceof Error ? error.message : "Unknown error",
      venueId,
    });
    return null;
  }
}

/**
 * Save venue data to cache
 */
export async function saveVenueCache(
  venueId: string,
  data: Partial<VenueCacheData>
): Promise<boolean> {
  try {
    console.log("[Firebase] Saving cache for venue:", venueId);
    console.log("[Firebase] Data to save:", data);

    const venueDoc = doc(db, "venues", venueId);

    // Get existing data to merge with new data
    const snapshot = await getDoc(venueDoc);
    const existingData = snapshot.exists() ? snapshot.data() : {};

    // Merge and save
    const updatedData = {
      ...existingData,
      ...data,
      lastUpdated: Date.now(),
    };

    console.log("[Firebase] Merged data:", updatedData);
    await setDoc(venueDoc, updatedData, { merge: true });
    console.log("[Firebase] Successfully saved cache");
    return true;
  } catch (error) {
    console.error("[Firebase] Error saving venue cache:", error);
    console.error("[Firebase] Error details:", {
      message: error instanceof Error ? error.message : "Unknown error",
      venueId,
      data,
    });
    return false;
  }
}

/**
 * Update only AI insights for a venue
 */
export async function saveAiInsights(
  venueId: string,
  aiInsights: string
): Promise<boolean> {
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
export async function getTrendingRestaurantsCache(
  maxAgeMs: number = 7 * 24 * 60 * 60 * 1000
): Promise<TrendingRestaurant[] | null> {
  try {
    console.log("[Firebase] Getting trending restaurants cache");

    const cacheDoc = doc(db, "cache", "trending");
    const snapshot = await getDoc(cacheDoc);

    if (snapshot.exists()) {
      const data = snapshot.data() as TrendingRestaurantsCacheData;
      const age = Date.now() - data.lastUpdated;

      console.log(
        `[Firebase] Cache found. Age: ${Math.floor(age / 1000 / 60)} minutes`
      );

      if (age < maxAgeMs) {
        console.log("[Firebase] Cache is still valid");
        return data.restaurants;
      } else {
        console.log("[Firebase] Cache expired");
        return null;
      }
    }

    console.log("[Firebase] No cache found");
    return null;
  } catch (error) {
    console.error(
      "[Firebase] Error getting trending restaurants cache:",
      error
    );
    return null;
  }
}

/**
 * Save trending restaurants to cache
 */
export async function saveTrendingRestaurantsCache(
  restaurants: TrendingRestaurant[]
): Promise<boolean> {
  try {
    console.log("[Firebase] Saving trending restaurants cache");

    const cacheDoc = doc(db, "cache", "trending");
    const cacheData: TrendingRestaurantsCacheData = {
      restaurants,
      lastUpdated: Date.now(),
    };

    await setDoc(cacheDoc, cacheData);
    console.log("[Firebase] Successfully saved trending restaurants cache");
    return true;
  } catch (error) {
    console.error("[Firebase] Error saving trending restaurants cache:", error);
    return false;
  }
}

/**
 * Get cached top-rated restaurants
 * @param maxAgeMs - Maximum age of cache in milliseconds (default: 7 days)
 * @returns Cached data if valid, null otherwise
 */
export async function getTopRatedRestaurantsCache(
  maxAgeMs: number = 7 * 24 * 60 * 60 * 1000
): Promise<TrendingRestaurant[] | null> {
  try {
    console.log("[Firebase] Getting top-rated restaurants cache");

    const cacheDoc = doc(db, "cache", "topRated");
    const snapshot = await getDoc(cacheDoc);

    if (snapshot.exists()) {
      const data = snapshot.data() as TrendingRestaurantsCacheData;
      const age = Date.now() - data.lastUpdated;

      console.log(
        `[Firebase] Cache found. Age: ${Math.floor(age / 1000 / 60)} minutes`
      );

      if (age < maxAgeMs) {
        console.log("[Firebase] Cache is still valid");
        return data.restaurants;
      } else {
        console.log("[Firebase] Cache expired");
        return null;
      }
    }

    console.log("[Firebase] No cache found");
    return null;
  } catch (error) {
    console.error(
      "[Firebase] Error getting top-rated restaurants cache:",
      error
    );
    return null;
  }
}

/**
 * Save top-rated restaurants to cache
 */
export async function saveTopRatedRestaurantsCache(
  restaurants: TrendingRestaurant[]
): Promise<boolean> {
  try {
    console.log("[Firebase] Saving top-rated restaurants cache");

    const cacheDoc = doc(db, "cache", "topRated");
    const cacheData: TrendingRestaurantsCacheData = {
      restaurants,
      lastUpdated: Date.now(),
    };

    await setDoc(cacheDoc, cacheData);
    console.log("[Firebase] Successfully saved top-rated restaurants cache");
    return true;
  } catch (error) {
    console.error(
      "[Firebase] Error saving top-rated restaurants cache:",
      error
    );
    return false;
  }
}

// ===== USER BOOKMARKS FUNCTIONS =====

/**
 * Add a venue to user's bookmarks
 */
export async function addBookmark(
  userId: string,
  bookmarkData: BookmarkData
): Promise<boolean> {
  try {
    console.log(
      "[Firebase] Adding bookmark for user:",
      userId,
      "venue:",
      bookmarkData.venueId
    );

    const bookmarkDoc = doc(
      db,
      "users",
      userId,
      "bookmarks",
      bookmarkData.venueId
    );
    await setDoc(bookmarkDoc, {
      ...bookmarkData,
      bookmarkedAt: Date.now(),
    });

    console.log("[Firebase] Successfully added bookmark");
    return true;
  } catch (error) {
    console.error("[Firebase] Error adding bookmark:", error);
    return false;
  }
}

/**
 * Remove a venue from user's bookmarks
 */
export async function removeBookmark(
  userId: string,
  venueId: string
): Promise<boolean> {
  try {
    console.log(
      "[Firebase] Removing bookmark for user:",
      userId,
      "venue:",
      venueId
    );

    const bookmarkDoc = doc(db, "users", userId, "bookmarks", venueId);
    await deleteDoc(bookmarkDoc);

    console.log("[Firebase] Successfully removed bookmark");
    return true;
  } catch (error) {
    console.error("[Firebase] Error removing bookmark:", error);
    return false;
  }
}

/**
 * Get all bookmarks for a user
 */
export async function getUserBookmarks(
  userId: string
): Promise<BookmarkData[]> {
  try {
    console.log("[Firebase] Getting bookmarks for user:", userId);

    const bookmarksCol = collection(db, "users", userId, "bookmarks");
    const snapshot = await getDocs(bookmarksCol);

    const bookmarks: BookmarkData[] = [];
    snapshot.forEach((doc) => {
      bookmarks.push(doc.data() as BookmarkData);
    });

    // Sort by bookmarkedAt descending (most recent first)
    bookmarks.sort((a, b) => b.bookmarkedAt - a.bookmarkedAt);

    console.log("[Firebase] Found", bookmarks.length, "bookmarks");
    return bookmarks;
  } catch (error) {
    console.error("[Firebase] Error getting bookmarks:", error);
    return [];
  }
}

/**
 * Check if a venue is bookmarked by user
 */
export async function isVenueBookmarked(
  userId: string,
  venueId: string
): Promise<boolean> {
  try {
    const bookmarkDoc = doc(db, "users", userId, "bookmarks", venueId);
    const snapshot = await getDoc(bookmarkDoc);
    return snapshot.exists();
  } catch (error) {
    console.error("[Firebase] Error checking bookmark:", error);
    return false;
  }
}

export interface ReservationSnipeRequest {
  venueId: string;
  partySize: number;
  date: string; // "yyyy-MM-dd"
  dropDate: string; // "yyyy-MM-dd"
  hour: number; // reservation time hour (for TimedReservationRequest)
  minute: number; // reservation time minute
  dropHour: number; // expected drop hour (when Resy releases)
  dropMinute: number; // expected drop minute
  windowHours?: number;
  seatingType?: string;
  userId?: string | null;
  actuallyReserve?: boolean;
}

export interface ReservationSnipeResponse {
  jobId: string;
  targetTimeIso: string;
}

/**
 * Schedule a reservation snipe with the backend (Cloud Run / Cloud Functions).
 * This:
 *  - writes a Firestore job document
 *  - creates ONE Cloud Scheduler job
 */
export async function scheduleReservationSnipe(
  request: ReservationSnipeRequest
): Promise<ReservationSnipeResponse> {
  try {
    const fullRequest = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    };

    let response: Response;
    if (useEmulators) {
      console.log("[Firebase Emulator] Scheduling snipe directly in emulator");
      // In emulator mode, create the Firestore job document directly
      // This mimics what the backend does in schedule.py

      // Create target datetime in America/New_York timezone
      const [dropYear, dropMonth, dropDay] = request.dropDate
        .split("-")
        .map(Number);
      const targetDate = new Date(
        dropYear,
        dropMonth - 1,
        dropDay,
        request.dropHour,
        request.dropMinute
      );

      // Format as ISO 8601 with timezone offset for America/New_York
      // Note: This is a simplified version. In production, the backend handles timezone conversion properly
      const targetTimeIso = new Date(
        targetDate.getTime() - targetDate.getTimezoneOffset() * 60000
      )
        .toISOString()
        .replace("Z", "-05:00"); // EST offset (simplified)

      // Create a new job document reference
      const jobRef = doc(collection(db, "reservationJobs"));
      const jobId = jobRef.id;

      const jobData = {
        jobId,
        userId: request.userId || null,
        venueId: request.venueId,
        partySize: request.partySize,
        // Reservation info
        date: request.date,
        hour: request.hour,
        minute: request.minute,
        // Drop info
        dropDate: request.dropDate,
        dropHour: request.dropHour,
        dropMinute: request.dropMinute,
        // Job/meta
        status: "pending",
        targetTimeIso,
        createdAt: Timestamp.now(),
        lastUpdate: Timestamp.now(),
        // Extra options
        windowHours: request.windowHours || 1,
        seatingType: request.seatingType || null,
      };

      // Write the job document to Firestore
      await setDoc(jobRef, jobData);

      console.log(
        `[Firebase Emulator] Created job document ${jobId} in reservationJobs collection`
      );

      const user = auth.currentUser;

      // Now call run_snipe to actually run the snipe immediately

      if (request.actuallyReserve) {
        response = await fetch(
          `${CLOUD_FUNCTIONS_BASE}/run_snipe?userId=${user!.uid}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ jobId }),
          }
        );
        return {
          jobId: "EMULATOR: TRUE RUN",
          targetTimeIso: "Random time",
        };
      }
      return {
        jobId: "EMULATOR: FALSE RUN",
        targetTimeIso: "Random time",
      };
    } else {
      response = await fetch(CREATE_SNIPE_URL, fullRequest);
    }

    console.log(
      "[Firebase] Requested scheduleReservationSnipe with request:",
      fullRequest,
      "at URL:",
      CREATE_SNIPE_URL
    );

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      console.error("[Firebase] scheduleReservationSnipe error:", errorBody);
      throw new Error(
        errorBody.error || "Failed to schedule reservation snipe"
      );
    }

    const result = (await response.json()) as {
      success: boolean;
      jobId?: string;
      targetTimeIso?: string;
      error?: string;
    };

    if (!result.success || !result.jobId || !result.targetTimeIso) {
      throw new Error(result.error || "Failed to schedule reservation snipe");
    }

    console.log("[Firebase] Scheduled snipe:", result);

    return {
      jobId: result.jobId,
      targetTimeIso: result.targetTimeIso,
    };
  } catch (err) {
    console.error("[Firebase] scheduleReservationSnipe failed:", err);
    throw err;
  }
}

// ===== RESERVATION JOBS FUNCTIONS =====

export interface ReservationJob {
  jobId: string;
  userId?: string;
  venueId: string;
  partySize: number;
  date: string; // "YYYY-MM-DD" - reservation date
  hour: number;
  minute: number;
  dropDate: string; // "YYYY-MM-DD" - drop date
  dropHour: number;
  dropMinute: number;
  status: "pending" | "done" | "failed" | "error";
  targetTimeIso: string;
  createdAt: Timestamp;
  lastUpdate: Timestamp;
  windowHours?: number;
  seatingType?: string;
  resyToken?: string;
  errorMessage?: string;
}

/**
 * Get all reservation jobs for a user
 */
export async function getUserReservationJobs(
  userId: string
): Promise<ReservationJob[]> {
  try {
    console.log("[Firebase] Getting reservation jobs for user:", userId);

    const jobsQuery = query(
      collection(db, "reservationJobs"),
      where("userId", "==", userId),
      orderBy("createdAt", "desc")
    );

    const snapshot = await getDocs(jobsQuery);

    const jobs: ReservationJob[] = snapshot.docs.map((doc) => {
      const data = doc.data() as ReservationJob;
      return {
        ...data,
        jobId: doc.id,
      };
    });

    console.log("[Firebase] Found", jobs.length, "reservation jobs");
    return jobs;
  } catch (error) {
    console.error("[Firebase] Error getting reservation jobs:", error);
    return [];
  }
}

export { db, analytics, auth, googleProvider, CLOUD_FUNCTIONS_BASE };
