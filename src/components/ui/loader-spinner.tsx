import * as React from "react";
import { LoaderCircle } from "lucide-react";

import { cn } from "@/lib/utils";

const sizeClasses = {
  sm: "size-4",
  default: "size-6",
  lg: "size-12",
} as const;

interface LoaderSpinnerProps extends React.SVGProps<SVGSVGElement> {
  size?: keyof typeof sizeClasses;
  className?: string;
}

function LoaderSpinner({
  size = "default",
  className,
  ...props
}: LoaderSpinnerProps) {
  return (
    <LoaderCircle
      className={cn(sizeClasses[size], "animate-spin shrink-0", className)}
      aria-hidden
      {...props}
    />
  );
}

export { LoaderSpinner };
