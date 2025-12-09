import React, { useState } from "react";
import { ChevronRight, MapPin } from "lucide-react";

export interface SearchResultItemProps {
  id: string;
  name: string;
  type?: string;
  priceRange: number;
  location?: string;
  imageUrl?: string | null;
  onCardClick?: (id: string) => void;
  onHover?: (id: string | null) => void;
  availableTimes?: string[]; // Array of available time slots (max 4)
  availabilityStatus?: string; // Status message when no times available
  showPlaceholder?: boolean; // If true, show "TODO: AI Summary" instead of times
  imageSize?: "small" | "large"; // Size of the image thumbnail
}

export const SearchResultItem = React.memo(function SearchResultItem({
  id,
  name,
  type,
  priceRange,
  location,
  imageUrl,
  onCardClick,
  onHover,
  availableTimes,
  availabilityStatus,
  showPlaceholder,
  imageSize,
}: SearchResultItemProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleImageLoad = () => {
    setImageLoaded(true);
    setImageError(false);
  };

  const handleImageError = () => {
    setImageError(true);
    setImageLoaded(true);
  };

  return (
    <button
      onClick={() => onCardClick?.(id)}
      onMouseEnter={() => onHover?.(id)}
      onMouseLeave={() => onHover?.(null)}
      className="w-full text-left px-4 py-3 hover:bg-accent transition-colors border-2 border-background rounded-md"
    >
      <div className="flex flex-row relative items-start gap-3 h-full">
        {/* Image Thumbnail */}
        {imageUrl && !imageError && (
          <div
            className={`shrink-0 ${
              imageSize === "small" ? "w-16 h-16" : "w-32 h-32"
            } rounded-md overflow-hidden bg-muted relative`}
          >
            {!imageLoaded && (
              <div className="absolute inset-0 w-full h-full bg-muted animate-pulse" />
            )}
            <img
              key={imageUrl}
              src={imageUrl}
              alt={name}
              className={`w-full h-full object-cover transition-opacity duration-300 ${
                imageLoaded ? "opacity-100" : "opacity-0"
              }`}
              onLoad={handleImageLoad}
              onError={handleImageError}
            />
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 justify-between">
            <div className="flex flex-row items-center gap-2">
              <h4
                className={`font-semibold underline-offset-4 hover:underline wrap-break-word ${
                  imageSize === "small" ? "text-md" : "text-lg"
                } px-0 truncate`}
              >
                {name}
              </h4>
              {priceRange > 0 && (
                <span className="text-sm text-muted-foreground font-medium shrink-0">
                  {"$".repeat(priceRange)}
                </span>
              )}
            </div>
          </div>

          {type && type !== "N/A" && (
            <p className="text-xs text-muted-foreground truncate mb-1">
              {type}
            </p>
          )}

          {location && (
            <div
              className={`flex items-center gap-1 ${
                imageSize === "small" ? "text-xs" : "text-sm"
              } text-muted-foreground`}
            >
              <MapPin className="size-3 shrink-0" />
              <span className="truncate">{location}</span>
            </div>
          )}

          {/* Reservation Times or Placeholder */}
          {showPlaceholder && (
            <div className="mt-2 text-xs text-muted-foreground italic">
              {/* TODO: AI Summary */}
            </div>
          )}

          {availableTimes && availableTimes.length > 0 && (
            <div className="mt-2">
              <div className="flex flex-wrap gap-1">
                {availableTimes.slice(0, 8).map((time, index) => (
                  <span
                    key={index}
                    className="text-md px-3 py-1 bg-blue-600 text-white rounded-md font-medium"
                  >
                    {time}
                  </span>
                ))}
              </div>
            </div>
          )}

          {!availableTimes && availabilityStatus && (
            <div className="mt-2">
              <span
                className={`text-sm px-2 py-1 text-muted-foreground rounded-md ${
                  availabilityStatus === "Sold out"
                    ? "bg-red-500 text-white"
                    : availabilityStatus === "Not released yet"
                    ? "bg-linear-to-r from-indigo-500 via-purple-500 to-pink-500 text-white font-semibold animate-gradient-flow"
                    : "bg-zinc-200"
                }`}
              >
                {availabilityStatus}
              </span>
            </div>
          )}
        </div>

        <div className="hidden sm:block absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2">
          <ChevronRight />
        </div>
      </div>
    </button>
  );
});
