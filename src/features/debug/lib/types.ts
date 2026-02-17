/**
 * Types for the Resy API debug dashboard and /resy_debug backend response.
 */

export type ResyDebugEndpointName =
  | "calendar"
  | "find"
  | "venue"
  | "search"
  | "city_list"
  | "all";

export interface ResyDebugAuthResult {
  status: "ok" | "error";
  token_preview?: string;
  time_ms?: number | null;
  message?: string;
}

export interface ResyDebugEndpointResult {
  endpoint: string;
  method: string;
  request_params: Record<string, unknown>;
  status_code: number | null;
  time_ms: number | null;
  rate_limit_headers: Record<string, string>;
  raw_response: unknown;
  schema_valid: boolean | null;
  schema_errors: string | null;
  error?: string;
}

export interface ResyDebugResponse {
  success: boolean;
  auth: ResyDebugAuthResult | null;
  results: ResyDebugEndpointResult[];
  error: string | null;
}

export interface ResyDebugRequest {
  endpoint: ResyDebugEndpointName;
  params?: Record<string, string | number>;
}
