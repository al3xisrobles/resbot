import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiPost, API_ENDPOINTS } from "@/lib/apiClient";
import { ResponseViewer } from "./ResponseViewer";
import type {
  ResyDebugEndpointName,
  ResyDebugEndpointResult,
  ResyDebugResponse,
} from "../lib/types";

type SingleEndpoint = Exclude<ResyDebugEndpointName, "all">;

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function endDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 90);
  return d.toISOString().slice(0, 10);
}

const DEFAULT_PARAMS: Record<SingleEndpoint, Record<string, string | number>> = {
  calendar: {
    venue_id: "2",
    num_seats: 2,
    start_date: today(),
    end_date: endDate(),
  },
  find: {
    venue_id: 2,
    day: today(),
    party_size: 2,
  },
  venue: {
    venue_id: "2",
  },
  search: {
    query: "pizza",
  },
  city_list: {
    slug: "new-york-ny",
    list_type: "climbing",
    limit: 10,
  },
};

interface EndpointTesterProps {
  endpoint: SingleEndpoint;
}

export function EndpointTester({ endpoint }: EndpointTesterProps) {
  const [params, setParams] = React.useState<Record<string, string | number>>(
    () => ({ ...DEFAULT_PARAMS[endpoint] })
  );
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<ResyDebugEndpointResult | null>(
    null
  );
  const [error, setError] = React.useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const response = await apiPost<ResyDebugResponse>(
        API_ENDPOINTS.resyDebug,
        { endpoint, params }
      );
      if (response.results?.length) {
        setResult(response.results[0]);
      }
      if (response.error) {
        setError(response.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const paramEntries = Object.entries(params);

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {paramEntries.map(([key, value]) => (
          <div key={key} className="space-y-1.5">
            <Label htmlFor={key}>{key}</Label>
            <Input
              id={key}
              value={String(value)}
              onChange={(e) =>
                setParams((prev) => ({
                  ...prev,
                  [key]:
                    key === "venue_id" && endpoint === "find"
                      ? parseInt(e.target.value, 10) || 0
                      : key === "num_seats" || key === "limit" || key === "party_size"
                        ? parseInt(e.target.value, 10) || 0
                        : e.target.value,
                }))
              }
            />
          </div>
        ))}
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "Sending…" : "Send request"}
      </Button>

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {result && (
        <div className="rounded-lg border p-4">
          <p className="mb-2 text-sm font-medium">Response</p>
          <ResponseViewer result={result} />
        </div>
      )}
    </form>
  );
}
