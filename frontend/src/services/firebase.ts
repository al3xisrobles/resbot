import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getDatabase, ref, get, set, Database } from "firebase/database";

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBRKnRKQm-5Xy7UmAkBR1vLNWUU45PAfYo",
  authDomain: "resybot-5bb59.firebaseapp.com",
  projectId: "resybot-5bb59",
  storageBucket: "resybot-5bb59.firebasestorage.app",
  messagingSenderId: "989852153876",
  appId: "1:989852153876:web:4f992021d186d244214f01",
  measurementId: "G-CRZCLH183E",
  databaseURL: "https://resybot-5bb59-default-rtdb.firebaseio.com"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const database = getDatabase(app);

export interface VenueCacheData {
  aiInsights?: string;
  googleMapsLink?: string;
  resyLink?: string;
  beliLink?: string;
  photoUrl?: string;
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
    const venueRef = ref(database, `venues/${venueId}`);
    const snapshot = await get(venueRef);

    if (snapshot.exists()) {
      return snapshot.val() as VenueCacheData;
    }
    return null;
  } catch (error) {
    console.error('Error getting venue cache:', error);
    return null;
  }
}

/**
 * Save venue data to cache
 */
export async function saveVenueCache(venueId: string, data: Partial<VenueCacheData>): Promise<boolean> {
  try {
    const venueRef = ref(database, `venues/${venueId}`);

    // Get existing data to merge with new data
    const snapshot = await get(venueRef);
    const existingData = snapshot.exists() ? snapshot.val() : {};

    // Merge and save
    const updatedData = {
      ...existingData,
      ...data,
      lastUpdated: Date.now()
    };

    await set(venueRef, updatedData);
    return true;
  } catch (error) {
    console.error('Error saving venue cache:', error);
    return false;
  }
}

/**
 * Update only AI insights for a venue
 */
export async function saveAiInsights(venueId: string, aiInsights: string): Promise<boolean> {
  return saveVenueCache(venueId, { aiInsights });
}

export { database, analytics };
