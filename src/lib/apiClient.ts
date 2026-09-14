/**
 * Centralized API client for backend Cloud Functions
 * Handles trace header propagation and endpoint management
 */
import * as Sentry from "@sentry/react";
import { CLOUD_FUNCTIONS_BASE } from "../services/firebase";
import { triggerSessionExpiredModal } from "../contexts/ResySessionContext.utils";

/**
 * Custom error class for Resy session expiration (419 error)
 */
export class ResySessionExpiredError extends Error {
    constructor(message = "Resy session expired") {
        super(message);
        this.name = "ResySessionExpiredError";
    }
}

/**
 * Centralized endpoint definitions
 * All backend API endpoints should be defined here
 */
export const API_ENDPOINTS = {
    search: "/search",
    searchMap: "/search_map",
    venue: "/venue",
    venueLinks: "/venue_links",
    checkVenuePaymentRequirement: "/check_venue_payment_requirement",
    calendar: "/calendar",
    slots: "/slots",
    reservation: "/reservation",
    geminiSearch: "/gemini_search",
    summarizeSnipeLogs: "/summarize_snipe_logs",
    climbing: "/climbing",
    topRated: "/top_rated",
    health: "https://health-hypomglm7a-uc.a.run.app",
    // Onboarding endpoints
    startResyOnboarding: "/start_resy_onboarding",
    resyAccount: "/resy_account",
    // Auth endpoints
    me: "/me",
    // Snipe endpoints
    createSnipe: "/create_snipe",
    updateSnipe: "/update_snipe",
    cancelSnipe: "/cancel_snipe",
    runSnipe: "/run_snipe",
    // Debug
    resyDebug: "/resy_debug",
} as const;

/**
 * Build full URL for a Cloud Function endpoint
 */
function buildUrl(endpoint: string): string {
    // If endpoint already starts with http, return as-is (external URLs)
    if (endpoint.startsWith("http://") || endpoint.startsWith("https://")) {
        return endpoint;
    }
    return `${CLOUD_FUNCTIONS_BASE}${endpoint}`;
}

/** Typed error code the backend sends when the user's Resy session token is expired. */
const RESY_SESSION_EXPIRED_CODE = "RESY_SESSION_EXPIRED";

/**
 * Detect an expired/invalid Resy session and trigger the reconnect modal.
 *
 * The backend returns HTTP 419 (the same status Resy itself uses) with a typed
 * `code: "RESY_SESSION_EXPIRED"` body. We branch on those structured signals rather
 * than matching error text, so a wording change on either side can't break detection.
 */
async function handleApiResponse(response: Response): Promise<Response> {
    if (!response.ok) {
        // Primary signal: the backend's dedicated 419 status for an expired session.
        if (response.status === 419) {
            triggerSessionExpiredModal();
            throw new ResySessionExpiredError();
        }

        // Secondary signal: the typed code in the body, in case the 419 status is not
        // preserved by some intermediary.
        try {
            const errorData = await response.clone().json();
            if (errorData?.code === RESY_SESSION_EXPIRED_CODE) {
                triggerSessionExpiredModal();
                throw new ResySessionExpiredError();
            }
        } catch (e) {
            // Re-throw our own signal; ignore JSON parse failures on other errors.
            if (e instanceof ResySessionExpiredError) {
                throw e;
            }
        }
    }
    return response;
}

/**
 * Core API request function with automatic Sentry trace header injection
 * 
 * @param endpoint - Endpoint path (from API_ENDPOINTS) or full URL
 * @param options - Fetch options (method, body, headers, etc.)
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Promise with typed response data
 */
export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {},
    signal?: AbortSignal
): Promise<T> {
    const url = buildUrl(endpoint);
    const method = options.method || "GET";

    // Build headers with trace propagation
    const headers = new Headers(options.headers);

    // Note: Trace headers are automatically injected by Sentry's browserTracingIntegration
    // when tracePropagationTargets matches the URL. We don't need to manually inject them.

    // Ensure Content-Type is set for POST/PUT requests with JSON body
    if ((method === "POST" || method === "PUT" || method === "PATCH") && options.body) {
        if (!headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }
    }

    return Sentry.startSpan(
        {
            op: "http.client",
            name: `${method} ${endpoint}`,
        },
        async (span) => {
            try {
                span.setAttribute("http.url", url);
                span.setAttribute("http.method", method);

                // Add query params to span if URL has them
                const urlObj = new URL(url);
                if (urlObj.search) {
                    span.setAttribute("http.query", urlObj.search);
                }

                const response = await fetch(url, {
                    ...options,
                    headers,
                    signal,
                });

                span.setAttribute("http.status_code", response.status);

                const processedResponse = await handleApiResponse(response);

                if (!processedResponse.ok) {
                    const error = await processedResponse.json().catch(() => ({
                        error: `HTTP ${processedResponse.status}: ${processedResponse.statusText}`,
                    }));
                    const errorObj = new Error(error.error || `Failed ${method} ${endpoint}`);
                    span.setStatus({ code: 2 });
                    Sentry.captureException(errorObj);
                    throw errorObj;
                }

                const result = await processedResponse.json();
                span.setStatus({ code: 1 });
                return result as T;
            } catch (error) {
                // Don't capture ResySessionExpiredError or AbortError - they're expected behavior
                if (!(error instanceof ResySessionExpiredError) &&
                    !(error instanceof Error && error.name === 'AbortError')) {
                    Sentry.captureException(error);
                }
                span.setStatus({ code: 2 });
                throw error;
            }
        }
    );
}

/**
 * GET request helper
 */
export async function apiGet<T>(
    endpoint: string,
    params?: URLSearchParams | Record<string, string | number | boolean | undefined>,
    signal?: AbortSignal
): Promise<T> {
    let url = endpoint;

    if (params) {
        const searchParams = params instanceof URLSearchParams
            ? params
            : new URLSearchParams();

        if (!(params instanceof URLSearchParams)) {
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    searchParams.append(key, String(value));
                }
            });
        }

        const queryString = searchParams.toString();
        if (queryString) {
            url = `${endpoint}?${queryString}`;
        }
    }

    return apiRequest<T>(url, { method: "GET" }, signal);
}

/**
 * POST request helper
 */
export async function apiPost<T>(
    endpoint: string,
    body?: unknown,
    params?: URLSearchParams | Record<string, string | number | boolean | undefined>
): Promise<T> {
    let url = endpoint;

    if (params) {
        const searchParams = params instanceof URLSearchParams
            ? params
            : new URLSearchParams();

        if (!(params instanceof URLSearchParams)) {
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    searchParams.append(key, String(value));
                }
            });
        }

        const queryString = searchParams.toString();
        if (queryString) {
            url = `${endpoint}?${queryString}`;
        }
    }

    return apiRequest<T>(url, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
    });
}

/**
 * DELETE request helper
 */
export async function apiDelete<T>(
    endpoint: string,
    params?: URLSearchParams | Record<string, string | number | boolean | undefined>
): Promise<T> {
    let url = endpoint;

    if (params) {
        const searchParams = params instanceof URLSearchParams
            ? params
            : new URLSearchParams();

        if (!(params instanceof URLSearchParams)) {
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    searchParams.append(key, String(value));
                }
            });
        }

        const queryString = searchParams.toString();
        if (queryString) {
            url = `${endpoint}?${queryString}`;
        }
    }

    return apiRequest<T>(url, { method: "DELETE" });
}

/** Response shape from check_venue_payment_requirement */
interface CheckVenuePaymentRequirementResponse {
    success: boolean;
    data?: {
        requiresPaymentMethod?: boolean | null;
        source?: string;
        slotsAnalyzed?: number;
    };
    error?: string;
}

/**
 * Check if venue requires payment method.
 * Returns true (required), false (not required), or null (unknown).
 */
export async function checkVenuePaymentRequirement(
    venueId: string,
    userId?: string,
    date?: string,
    partySize?: number
): Promise<boolean | null> {
    const params: Record<string, string> = { id: venueId };
    if (userId) params.userId = userId;
    if (date) params.date = date;
    if (partySize !== undefined) params.partySize = String(partySize);

    const data = await apiGet<CheckVenuePaymentRequirementResponse>(
        API_ENDPOINTS.checkVenuePaymentRequirement,
        params
    );
    return data.data?.requiresPaymentMethod ?? null;
}
