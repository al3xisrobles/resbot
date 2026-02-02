/**
 * Jotai atoms for authentication state management
 * Manages user authentication state, session data (/me), loading states, and errors
 */
import type { User } from "firebase/auth";
import { atom, type Getter, type Setter } from "jotai";

/**
 * Response type from /me endpoint
 */
export interface MeResponse {
    success: boolean;
    onboardingStatus: "not_started" | "completed";
    hasPaymentMethod: boolean;
    resy: {
        email: string;
        firstName: string;
        lastName: string;
        paymentMethodId: number | null;
    } | null;
    error?: string;
}

// Core authentication state atoms
export const isAuthenticatedAtom = atom(false);
export const userAtom = atom<User | null>(null);
export const accessTokenAtom = atom<string | null>(null);

// Session data atom (from GET /me)
export const meAtom = atom<MeResponse | null>(null);

// Loading state atoms
// Starts as true to prevent routing decisions before auth state is resolved
export const isAuthLoadingAtom = atom(true);
export const isSigningInAtom = atom(false);
export const isSigningOutAtom = atom(false);

// Error state atom
export const authErrorAtom = atom<Error | null>(null);

// Derived atom for complete auth and session state
// Includes all auth state plus /me session data
export const authStateAtom = atom((get: Getter) => ({
    isAuthenticated: get(isAuthenticatedAtom),
    user: get(userAtom),
    accessToken: get(accessTokenAtom),
    isLoading: get(isAuthLoadingAtom) || get(isSigningInAtom) || get(isSigningOutAtom),
    error: get(authErrorAtom),
    // Session data from /me endpoint
    me: get(meAtom),
}));

// Derived atom: Check if user has completed onboarding
export const isOnboardedAtom = atom((get: Getter) => {
    const me = get(meAtom);
    return me?.onboardingStatus === "completed";
});

// Action atom to clear authentication state (for logout)
export const clearAuthStateAtom = atom(null, (_get: Getter, set: Setter) => {
    set(isAuthenticatedAtom, false);
    set(userAtom, null);
    set(accessTokenAtom, null);
    set(meAtom, null);
    set(authErrorAtom, null);
});

// Action atom to clear auth errors
export const clearAuthErrorAtom = atom(null, (_get: Getter, set: Setter) => {
    set(authErrorAtom, null);
});
