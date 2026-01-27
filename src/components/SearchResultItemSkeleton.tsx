import { SkeletonRect } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

export function SearchResultItemSkeleton() {
    return (
        <div className="w-full px-4 py-3">
            <div className="flex flex-row items-start gap-3">
                {/* Image skeleton */}
                <SkeletonRect width="96px" height="96px" rounding="8" className="shrink-0" />

                <div className="flex-1 min-w-0 space-y-2">
                    {/* Name and price skeleton */}
                    <div className="flex items-center gap-2">
                        <SkeletonRect width="60%" height="20px" rounding="8" />
                        <SkeletonRect width="40px" height="16px" rounding="8" />
                    </div>

                    {/* Type skeleton */}
                    <SkeletonRect width="40%" height="14px" rounding="8" />

                    {/* Location skeleton */}
                    <div className="flex items-center gap-1">
                        <SkeletonRect width="12px" height="12px" rounding="8" />
                        <SkeletonRect width="50%" height="14px" rounding="8" />
                    </div>

                    {/* Optional availability times skeleton */}
                    <div className="flex flex-wrap gap-1 mt-2">
                        <SkeletonRect width="60px" height="24px" rounding="8" />
                        <SkeletonRect width="60px" height="24px" rounding="8" />
                        <SkeletonRect width="60px" height="24px" rounding="8" />
                    </div>
                </div>
            </div>
            <Separator className="my-2" />
        </div>
    );
}
