import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Stack, Group } from "@/components/ui/layout";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiPost, API_ENDPOINTS } from "@/lib/apiClient";
import { EndpointTester } from "./EndpointTester";
import type {
  ResyDebugEndpointResult,
  ResyDebugResponse,
} from "../lib/types";

const ENDPOINT_LABELS: Record<string, string> = {
  calendar: "Calendar",
  find: "Find",
  venue: "Venue",
  search: "Search",
  city_list: "City list",
};

const SINGLE_ENDPOINTS = ["calendar", "find", "venue", "search", "city_list"] as const;

function statusColor(result: ResyDebugEndpointResult): string {
  const code = result.status_code;
  if (result.error) return "border-muted bg-muted/30";
  if (code === null) return "border-muted bg-muted/30";
  if (code >= 200 && code < 300) return "border-green-500/50 bg-green-500/10";
  if (code === 429) return "border-yellow-500/50 bg-yellow-500/10";
  return "border-red-500/50 bg-red-500/10";
}

export function DebugDashboard() {
  const [healthResults, setHealthResults] = React.useState<
    ResyDebugEndpointResult[] | null
  >(null);
  const [healthLoading, setHealthLoading] = React.useState(false);
  const [healthError, setHealthError] = React.useState<string | null>(null);

  const runHealthCheck = React.useCallback(async () => {
    setHealthLoading(true);
    setHealthResults(null);
    setHealthError(null);
    try {
      const response = await apiPost<ResyDebugResponse>(
        API_ENDPOINTS.resyDebug,
        { endpoint: "all", params: {} }
      );
      if (response.results?.length) {
        setHealthResults(response.results);
      }
      if (response.error) {
        setHealthError(response.error);
      }
    } catch (err) {
      setHealthError(err instanceof Error ? err.message : String(err));
    } finally {
      setHealthLoading(false);
    }
  }, []);

  return (
    <Stack itemsSpacing={32}>
      <Stack itemsSpacing={16}>
        <Stack itemsSpacing={4}>
          <h2 className="text-xl font-semibold">Health grid</h2>
          <p className="text-muted-foreground text-sm">
            Probe all Resy endpoints at once. Green = 2xx, yellow = 429, red =
            error.
          </p>
        </Stack>
        <Group itemsSpacing={8} itemsAlignY="center" noWrap={false} className="flex-wrap">
          <Button
            type="button"
            variant="outline"
            onClick={runHealthCheck}
            disabled={healthLoading}
          >
            {healthLoading ? "Testing…" : "Test all"}
          </Button>
          {healthError && (
            <div className="rounded-md border border-destructive/50 bg-destructive/5 p-2 text-sm text-destructive">
              {healthError}
            </div>
          )}
        </Group>
        {healthResults && healthResults.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {healthResults.map((r, i) => {
              const label =
                ENDPOINT_LABELS[SINGLE_ENDPOINTS[i]] ?? r.endpoint;
              return (
                <Card
                  key={r.endpoint + String(i)}
                  className={statusColor(r)}
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{label}</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0 text-sm">
                    <Group itemsSpacing={8} itemsAlignY="center" noWrap={false} className="flex-wrap">
                      {r.status_code != null && (
                        <span className="font-mono">{r.status_code}</span>
                      )}
                      {r.time_ms != null && (
                        <span className="text-muted-foreground">
                          {r.time_ms} ms
                        </span>
                      )}
                      {r.schema_valid !== null && (
                        <span>
                          {r.schema_valid ? "✓ schema" : "✗ schema"}
                        </span>
                      )}
                    </Group>
                    {r.error && (
                      <p className="text-destructive mt-1 text-xs">{r.error}</p>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </Stack>

      <Stack itemsSpacing={16}>
        <Stack itemsSpacing={4}>
          <h2 className="text-xl font-semibold">Endpoint tester</h2>
          <p className="text-muted-foreground text-sm">
            Test one endpoint at a time with custom parameters.
          </p>
        </Stack>
        <Tabs defaultValue="calendar">
          <Stack itemsSpacing={12}>
            <TabsList className="flex-wrap">
              {SINGLE_ENDPOINTS.map((ep) => (
                <TabsTrigger key={ep} value={ep}>
                  {ENDPOINT_LABELS[ep] ?? ep}
                </TabsTrigger>
              ))}
            </TabsList>
            {SINGLE_ENDPOINTS.map((ep) => (
              <TabsContent key={ep} value={ep}>
                <EndpointTester endpoint={ep} />
              </TabsContent>
            ))}
          </Stack>
        </Tabs>
      </Stack>
    </Stack>
  );
}
