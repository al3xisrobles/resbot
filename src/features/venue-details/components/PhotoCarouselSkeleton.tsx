import { SkeletonRect } from "@/components/ui/skeleton";

export function PhotoCarouselSkeleton() {
  return (
    <div className="relative rounded-lg overflow-hidden">
      <SkeletonRect width="100%" height="400px" rounding="12" />
      {/* Pagination dots skeleton */}
      <div className="absolute left-1/2 bottom-3 -translate-x-1/2 z-10">
        <div className="flex items-center gap-2 rounded-full bg-background px-3 py-1 shadow-sm">
          {Array.from({ length: 3 }, (_, i) => (
            <SkeletonRect key={i} width="8px" height="8px" rounding="8" />
          ))}
        </div>
      </div>
    </div>
  );
}
