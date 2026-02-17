import * as React from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { ResyDebugEndpointResult } from "../lib/types";

interface ResponseViewerProps {
  result: ResyDebugEndpointResult;
  className?: string;
}

function statusBadgeClass(statusCode: number | null): string {
  if (statusCode === null) return "bg-muted text-muted-foreground";
  if (statusCode >= 200 && statusCode < 300) return "bg-green-500/10 text-green-600 dark:text-green-400";
  if (statusCode === 429) return "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400";
  return "bg-red-500/10 text-red-600 dark:text-red-400";
}

export function ResponseViewer({ result, className }: ResponseViewerProps) {
  const [open, setOpen] = React.useState(false);
  const statusCode = result.status_code;
  const rawJson =
    typeof result.raw_response === "string"
      ? result.raw_response
      : JSON.stringify(result.raw_response, null, 2);

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-2">
        {statusCode !== null && (
          <span
            className={cn(
              "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
              statusBadgeClass(statusCode)
            )}
          >
            {statusCode}
          </span>
        )}
        {result.time_ms != null && (
          <span className="text-muted-foreground text-xs">
            {result.time_ms} ms
          </span>
        )}
        {result.schema_valid !== null && (
          <span
            className={cn(
              "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
              result.schema_valid
                ? "bg-green-500/10 text-green-600 dark:text-green-400"
                : "bg-red-500/10 text-red-600 dark:text-red-400"
            )}
          >
            {result.schema_valid ? "Schema valid" : "Schema invalid"}
          </span>
        )}
      </div>

      {result.schema_errors && (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm text-destructive">
          <p className="font-medium">Schema validation errors</p>
          <pre className="mt-1 whitespace-pre-wrap wrap-break-word font-mono text-xs">
            {result.schema_errors}
          </pre>
        </div>
      )}

      {Object.keys(result.rate_limit_headers).length > 0 && (
        <div className="rounded-md border bg-muted/50 p-2 text-xs">
          <p className="font-medium text-muted-foreground">Rate limit headers</p>
          <pre className="mt-1 font-mono">
            {JSON.stringify(result.rate_limit_headers, null, 2)}
          </pre>
        </div>
      )}

      {result.error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm text-destructive">
          {result.error}
        </div>
      )}

      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="text-muted-foreground hover:text-foreground text-sm font-medium underline-offset-4 hover:underline">
          {open ? "Hide" : "Show"} raw response
        </CollapsibleTrigger>
        <CollapsibleContent>
          <pre className="mt-2 max-h-96 overflow-auto rounded-md border bg-muted/30 p-3 font-mono text-xs">
            {rawJson}
          </pre>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
