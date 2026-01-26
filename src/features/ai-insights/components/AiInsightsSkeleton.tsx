import { SkeletonRect, SkeletonText } from "@/components/ui/skeleton";

export function AiInsightsSkeleton() {
  return (
    <div className="space-y-4">
      {/* Header with icon and title */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SkeletonRect width="20px" height="20px" rounding="8" />
          <SkeletonRect width="180px" height="28px" rounding="8" />
        </div>
        <SkeletonRect width="80px" height="32px" rounding="8" />
      </div>
      {/* Description */}
      <SkeletonRect width="100%" height="16px" rounding="8" />
      {/* Last updated */}
      <SkeletonRect width="140px" height="14px" rounding="8" />
      {/* Summary text - multiple lines */}
      <SkeletonText numberOfLines={4} textSize="body" />
    </div>
  );
}
