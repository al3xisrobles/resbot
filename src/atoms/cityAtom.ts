import { atom } from "jotai";
import { DEFAULT_CITY_ID, getCityConfig, type CityConfig } from "@/lib/cities";

const CITY_STORAGE_KEY = "resbot_selected_city";

/**
 * Get the initial city ID from localStorage or default to NYC
 */
function getInitialCityId(): string {
    if (typeof window === "undefined") {
        return DEFAULT_CITY_ID;
    }
    const stored = localStorage.getItem(CITY_STORAGE_KEY);
    if (stored && typeof stored === "string") {
        return stored;
    }
    return DEFAULT_CITY_ID;
}

/**
 * Base atom for selected city ID
 */
const cityIdAtomBase = atom<string>(getInitialCityId());

/**
 * City atom with localStorage persistence
 * When the city changes, it automatically saves to localStorage
 */
export const cityAtom = atom(
    (get) => get(cityIdAtomBase),
    (get, set, newCityId: string) => {
        set(cityIdAtomBase, newCityId);
        if (typeof window !== "undefined") {
            localStorage.setItem(CITY_STORAGE_KEY, newCityId);
        }
    }
);

/**
 * Derived atom that returns the full CityConfig for the selected city
 */
export const cityConfigAtom = atom<CityConfig>((get) => {
    const cityId = get(cityAtom);
    return getCityConfig(cityId);
});
