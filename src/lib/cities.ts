/**
 * City configuration constants for multi-city support
 */

export interface CityConfig {
    id: string;
    name: string;
    center: [number, number]; // [lat, lng]
    bounds: {
        sw: [number, number]; // Southwest corner [lat, lng]
        ne: [number, number]; // Northeast corner [lat, lng]
    };
    radius: number; // Default search radius in meters
    timezone: string; // IANA timezone string (e.g., "America/New_York")
    timezoneAbbr: string; // Short timezone abbreviation for display (e.g., "ET", "PT")
}

export const CITIES: Record<string, CityConfig> = {
    nyc: {
        id: "nyc",
        name: "New York City",
        center: [40.7589, -73.9851], // Times Square
        bounds: {
            sw: [40.7, -74.02],
            ne: [40.8, -73.93],
        },
        radius: 16100, // ~10 miles
        timezone: "America/New_York",
        timezoneAbbr: "ET",
    },
    chicago: {
        id: "chicago",
        name: "Chicago",
        center: [41.8781, -87.6298],
        bounds: {
            sw: [41.7, -87.9],
            ne: [42.0, -87.5],
        },
        radius: 16100, // ~10 miles
        timezone: "America/Chicago",
        timezoneAbbr: "CT",
    },
    losAngeles: {
        id: "losAngeles",
        name: "Los Angeles",
        center: [34.0522, -118.2437],
        bounds: {
            sw: [33.7, -118.7],
            ne: [34.3, -118.0],
        },
        radius: 16100, // ~10 miles
        timezone: "America/Los_Angeles",
        timezoneAbbr: "PT",
    },
    sanFrancisco: {
        id: "sanFrancisco",
        name: "San Francisco",
        center: [37.7749, -122.4194],
        bounds: {
            sw: [37.7, -122.6],
            ne: [37.8, -122.3],
        },
        radius: 16100, // ~10 miles
        timezone: "America/Los_Angeles",
        timezoneAbbr: "PT",
    },
    boston: {
        id: "boston",
        name: "Boston",
        center: [42.3601, -71.0589],
        bounds: {
            sw: [42.2, -71.2],
            ne: [42.4, -70.9],
        },
        radius: 16100, // ~10 miles
        timezone: "America/New_York",
        timezoneAbbr: "ET",
    },
};

export const DEFAULT_CITY_ID = "nyc";

export function getCityConfig(cityId: string): CityConfig {
    return CITIES[cityId] || CITIES[DEFAULT_CITY_ID];
}
