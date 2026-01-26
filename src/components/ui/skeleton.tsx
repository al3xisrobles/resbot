import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-accent animate-pulse rounded-md", className)}
      {...props}
    />
  )
}

interface SkeletonRectProps {
  width: string | number;
  height: string | number;
  className?: string;
  rounding?: string;
}

function SkeletonRect({ className, width, height, rounding = "12" }: SkeletonRectProps) {
  const widthStyle = typeof width === "number" ? `${width}px` : width;
  const heightStyle = typeof height === "number" ? `${height}px` : height;
  const roundingClass = rounding === "8" ? "rounded-lg" : rounding === "12" ? "rounded-xl" : `rounded-[${rounding}px]`;

  return (
    <div
      className={cn("bg-accent animate-pulse", roundingClass, className)}
      style={{ width: widthStyle, height: heightStyle }}
    />
  );
}

interface SkeletonCircleProps {
  size?: "small" | "medium" | "large" | string | number;
  className?: string;
}

function SkeletonCircle({ className, size = "medium" }: SkeletonCircleProps) {
  const getSizeStyle = () => {
    if (typeof size === "number") {
      return { width: `${size}px`, height: `${size}px` };
    }
    const sizeMap = {
      small: "24px",
      medium: "32px",
      large: "64px",
    };
    return {
      width: sizeMap[size as keyof typeof sizeMap] || size,
      height: sizeMap[size as keyof typeof sizeMap] || size,
    };
  };

  return (
    <div
      className={cn("bg-accent animate-pulse rounded-full", className)}
      style={getSizeStyle()}
    />
  );
}

interface SkeletonTextProps {
  numberOfLines: number;
  textSize?: "page" | "section" | "subsection" | "group" | "subgroup" | "minor" | "body" | "caption" | string | number;
  className?: string;
}

function SkeletonText({
  className,
  textSize = "body",
  numberOfLines = 1,
}: SkeletonTextProps) {
  const getHeight = () => {
    if (typeof textSize === "number") return `${textSize}px`;

    const sizeMap: Record<string, string> = {
      page: "2.5rem",
      section: "2rem",
      subsection: "1.5rem",
      group: "1.25rem",
      subgroup: "1.125rem",
      minor: "1rem",
      body: "1rem",
      caption: "0.875rem",
    };

    return sizeMap[textSize] || textSize;
  };

  // Generate widths deterministically based on index to avoid Math.random in render
  const getWidthForLine = (index: number) => {
    const widths = [70, 85, 75, 60, 90, 65, 80, 55];
    return `${widths[index % widths.length]}%`;
  };

  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: numberOfLines }, (_, index) => (
        <SkeletonRect
          key={index}
          width={getWidthForLine(index)}
          height={getHeight()}
          rounding="8"
        />
      ))}
    </div>
  );
}

export { Skeleton, SkeletonRect, SkeletonCircle, SkeletonText }
