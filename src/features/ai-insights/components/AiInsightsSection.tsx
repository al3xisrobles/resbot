import { useState } from "react";
import { Sparkles, RefreshCw, ChevronDown, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { SkeletonRect, SkeletonText } from "@/components/ui/skeleton";
import type { GeminiSearchResponse } from "../lib/types";
import { renderMarkdownBold } from "../lib/renderMarkdownBold.private";

interface AiInsightsSectionProps {
  aiSummary: GeminiSearchResponse | null;
  loadingAi: boolean;
  aiError: string | null;
  aiLastUpdated: number | null;
  onRefresh: () => void;
}

export function AiInsightsSection({
  aiSummary,
  loadingAi,
  aiError,
  aiLastUpdated,
  onRefresh,
}: AiInsightsSectionProps) {
  const [showAiDetails, setShowAiDetails] = useState(false);

  // Show content skeleton when AI is loading (both initial load and refresh)
  const showContentSkeleton = loadingAi;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="size-5" />
          <h2 className="text-2xl font-bold">Reservation Insights</h2>
        </div>
        {loadingAi && !aiSummary ? (
          // Show skeleton when AI is loading after page has loaded (no summary yet)
          <SkeletonRect width="95px" height="32px" rounding="8" />
        ) : aiSummary ? (
          // Show disabled button during refresh, enabled when not loading
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={loadingAi}
              className="gap-2"
            >
              <RefreshCw className="size-4" />
              Refresh
            </Button>
          </div>
        ) : null}
      </div>

      <p className="text-sm text-muted-foreground mb-1">
        AI-powered information about booking this restaurant
      </p>

      {showContentSkeleton ? (
        <>
          {/* Last updated skeleton */}
          <SkeletonRect width="140px" height="14px" rounding="8" />
          {/* Summary text skeleton */}
          <SkeletonText numberOfLines={4} textSize="body" />
        </>
      ) : (
        <>
          {aiLastUpdated && (
            <p className="text-xs mt-0 text-muted-foreground">
              Last updated:{" "}
              {new Date(aiLastUpdated).toLocaleString("en-US", {
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
                hour12: true,
              })}
            </p>
          )}

          {aiError && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{aiError}</AlertDescription>
            </Alert>
          )}

          {aiSummary && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="prose prose-sm max-w-none">
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {renderMarkdownBold(aiSummary.summary)}
                </p>
              </div>

              {/* Show Details Button */}
              {((aiSummary.groundingChunks &&
                aiSummary.groundingChunks.length > 0) ||
                (aiSummary.webSearchQueries &&
                  aiSummary.webSearchQueries.length > 0)) && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowAiDetails(!showAiDetails)}
                      className="w-full gap-2"
                    >
                      <ChevronDown
                        className={`size-4 transition-transform ${showAiDetails ? "rotate-180" : ""
                          }`}
                      />
                      {showAiDetails ? "Hide" : "Show"} Additional Details
                    </Button>

                    {showAiDetails && (
                      <div className="space-y-4">
                        {/* Grounding Chunks (Sources) */}
                        {aiSummary.groundingChunks &&
                          aiSummary.groundingChunks.length > 0 && (
                            <>
                              <Separator />
                              <div>
                                <p className="text-xs font-medium text-muted-foreground mb-2">
                                  Sources
                                </p>
                                <div className="space-y-2">
                                  {aiSummary.groundingChunks.map((chunk, idx) => (
                                    <div key={idx} className="text-xs">
                                      <a
                                        href={chunk.uri || "#"}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-start gap-2 text-primary hover:underline group"
                                      >
                                        <span className="shrink-0 font-medium">
                                          [{idx + 1}]
                                        </span>
                                        <div className="flex-1 min-w-0">
                                          <div className="flex items-center gap-1">
                                            <span className="font-medium truncate">
                                              {chunk.title}
                                            </span>
                                            <ExternalLink className="size-3 shrink-0" />
                                          </div>
                                          {chunk.snippet && (
                                            <p className="text-muted-foreground mt-0.5 line-clamp-2">
                                              {chunk.snippet}
                                            </p>
                                          )}
                                        </div>
                                      </a>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </>
                          )}

                        {/* Web Search Queries */}
                        {aiSummary.webSearchQueries &&
                          aiSummary.webSearchQueries.length > 0 && (
                            <>
                              <Separator />
                              <div>
                                <p className="text-xs font-medium text-muted-foreground mb-2">
                                  Search Queries Used
                                </p>
                                <div className="flex flex-wrap gap-2">
                                  {aiSummary.webSearchQueries.map((query, idx) => (
                                    <span
                                      key={idx}
                                      className="text-xs bg-secondary px-2 py-1 rounded-md"
                                    >
                                      {query}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </>
                          )}
                      </div>
                    )}
                  </>
                )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
