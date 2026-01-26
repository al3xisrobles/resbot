import { SkeletonRect } from "@/components/ui/skeleton";

export function VenueDetailsSkeleton() {
  return (
    <div className="space-y-4">
      {/* Restaurant name */}
      <SkeletonRect width="70%" height="36px" rounding="8" />
      {/* Type and action buttons row */}
      <div className="flex justify-between items-center">
        <SkeletonRect width="80px" height="20px" rounding="8" />
        <div className="flex gap-2">
          <SkeletonRect width="32px" height="32px" rounding="8" />
          <SkeletonRect width="32px" height="32px" rounding="8" />
        </div>
      </div>
      <div className="h-px bg-border" />
      {/* Address section */}
      <div className="flex items-start gap-3">
        <SkeletonRect width="20px" height="20px" rounding="8" />
        <div className="space-y-2 flex-1">
          <SkeletonRect width="60%" height="16px" rounding="8" />
          <SkeletonRect width="40%" height="14px" rounding="8" />
        </div>
      </div>
      {/* Price range section */}
      <div className="flex items-center gap-3">
        <SkeletonRect width="20px" height="20px" rounding="8" />
        <div className="space-y-1">
          <SkeletonRect width="100px" height="16px" rounding="8" />
          <SkeletonRect width="60px" height="14px" rounding="8" />
        </div>
      </div>
      {/* Action buttons */}
      <div className="flex gap-2 pt-4">
        <SkeletonRect width="120px" height="32px" rounding="8" />
        <SkeletonRect width="80px" height="32px" rounding="8" />
      </div>
    </div>
  );
}
