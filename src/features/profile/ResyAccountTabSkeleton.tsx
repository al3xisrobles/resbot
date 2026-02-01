import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonRect } from "@/components/ui/skeleton";

export function ResyAccountTabSkeleton() {
    return (
        <div className="space-y-6">
            {/* Connection Status Card */}
            <Card>
                <CardHeader>
                    <CardTitle>
                        <SkeletonRect width="180px" height="24px" rounding="8" />
                    </CardTitle>
                    <CardDescription>
                        <SkeletonRect width="250px" height="16px" rounding="8" />
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <SkeletonRect width="120px" height="16px" rounding="8" />
                        <div className="rounded-md border bg-muted/50 p-3 space-y-2">
                            <SkeletonRect width="150px" height="18px" rounding="8" />
                            <SkeletonRect width="200px" height="14px" rounding="8" />
                        </div>
                    </div>

                    <div className="flex gap-3">
                        <SkeletonRect width="140px" height="40px" rounding="8" />
                        <SkeletonRect width="120px" height="40px" rounding="8" />
                    </div>
                </CardContent>
            </Card>

            {/* Payment Methods Card */}
            <Card>
                <CardHeader>
                    <CardTitle>
                        <SkeletonRect width="160px" height="24px" rounding="8" />
                    </CardTitle>
                    <CardDescription>
                        <SkeletonRect width="280px" height="16px" rounding="8" />
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <SkeletonRect width="180px" height="16px" rounding="8" />
                        <SkeletonRect width="100%" height="40px" rounding="8" />
                    </div>

                    <div className="flex justify-end">
                        <SkeletonRect width="80px" height="40px" rounding="8" />
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
