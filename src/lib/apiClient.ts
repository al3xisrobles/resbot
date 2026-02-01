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

/**
 * Check if an API error response indicates a Resy session expiration (419)
 * and trigger the modal if so
 */
async function handleApiResponse(response: Response): Promise<Response> {
    if (!response.ok) {
        // Check for 419 or 500 with "Unauthorized" message (backend wraps 419 as 500)
        if (response.status === 419) {
            triggerSessionExpiredModal();
            throw new ResySessionExpiredError();
        }

        // Try to parse the error response to check for 419-related errors
        try {
            const errorData = await response.clone().json();
            // Backend returns 500 but the error message contains "419" or "Unauthorized"
            if (
                errorData.error?.includes("419") ||
                errorData.error?.includes("Unauthorized") ||
                (response.status === 500 && errorData.error?.includes("API returned status 419"))
            ) {
                triggerSessionExpiredModal();
                throw new ResySessionExpiredError();
            }
        } catch (e) {
            // If it's already a ResySessionExpiredError, re-throw it
            if (e instanceof ResySessionExpiredError) {
                throw e;
            }
            // Otherwise, continue with normal error handling
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
