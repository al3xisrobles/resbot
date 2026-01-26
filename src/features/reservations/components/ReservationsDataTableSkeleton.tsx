import { SkeletonRect } from "@/components/ui/skeleton";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

export function ReservationsDataTableSkeleton() {
    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-[200px]">Restaurant</TableHead>
                        <TableHead className="w-[150px]">Date</TableHead>
                        <TableHead className="w-[100px]">Time</TableHead>
                        <TableHead className="w-[100px] text-center">Party Size</TableHead>
                        <TableHead className="w-[120px]">Status</TableHead>
                        <TableHead>Notes</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {Array.from({ length: 5 }, (_, i) => (
                        <TableRow key={i}>
                            <TableCell>
                                <SkeletonRect width="150px" height="20px" rounding="8" />
                            </TableCell>
                            <TableCell>
                                <SkeletonRect width="100px" height="20px" rounding="8" />
                            </TableCell>
                            <TableCell>
                                <SkeletonRect width="70px" height="20px" rounding="8" />
                            </TableCell>
                            <TableCell className="text-center">
                                <SkeletonRect width="30px" height="20px" rounding="8" className="mx-auto" />
                            </TableCell>
                            <TableCell>
                                <SkeletonRect width="80px" height="24px" rounding="12" />
                            </TableCell>
                            <TableCell>
                                <SkeletonRect width="120px" height="16px" rounding="8" />
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
