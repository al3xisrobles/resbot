import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonCircle, SkeletonRect } from "@/components/ui/skeleton";

export function ProfileTabSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>
            <SkeletonRect width="200px" height="24px" rounding="8" />
          </CardTitle>
          <CardDescription>
            <SkeletonRect width="300px" height="16px" rounding="8" />
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Avatar */}
          <div className="flex items-center gap-4">
            <SkeletonCircle size={80} />
            <div>
              <SkeletonRect width="120px" height="16px" rounding="8" />
            </div>
          </div>

          {/* Display Name */}
          <div className="space-y-2">
            <SkeletonRect width="100px" height="16px" rounding="8" />
            <SkeletonRect width="100%" height="40px" rounding="8" />
          </div>

          {/* Email */}
          <div className="space-y-2">
            <SkeletonRect width="60px" height="16px" rounding="8" />
            <SkeletonRect width="100%" height="40px" rounding="8" />
          </div>

          {/* Account Created */}
          <div className="space-y-2">
            <SkeletonRect width="120px" height="16px" rounding="8" />
            <SkeletonRect width="150px" height="16px" rounding="8" />
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <SkeletonRect width="80px" height="40px" rounding="8" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
