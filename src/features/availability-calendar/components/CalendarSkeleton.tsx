import { SkeletonRect } from "@/components/ui/skeleton";

export function CalendarSkeleton() {
  return (
    <div className="space-y-4">
      {/* Month header */}
      <div className="flex justify-between items-center">
        <SkeletonRect width="120px" height="24px" rounding="8" />
        <div className="flex gap-2">
          <SkeletonRect width="32px" height="32px" rounding="8" />
          <SkeletonRect width="32px" height="32px" rounding="8" />
        </div>
      </div>
      {/* Day headers */}
      <div className="grid grid-cols-7 gap-2">
        {Array.from({ length: 7 }, (_, i) => (
          <SkeletonRect key={i} width="100%" height="20px" rounding="8" />
        ))}
      </div>
      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-2">
        {Array.from({ length: 35 }, (_, i) => (
          <SkeletonRect key={i} width="100%" height="40px" rounding="8" />
        ))}
      </div>
    </div>
  );
}
