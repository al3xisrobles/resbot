import { useState } from "react";
import { MapPin, Bookmark } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Toggle } from "@/components/ui/toggle";
import { cn } from "@/lib/utils";

export interface RestaurantGridCardProps {
  id: string;
  name: string;
  type?: string;
  priceRange: number;
  location?: string;
  imageUrl?: string | null;
  onClick?: () => void;
  availableTimes?: string[]; // Array of available time slots (max 4)
  showPlaceholder?: boolean; // If true, show "TODO: AI Summary" instead of times
}

export function RestaurantGridCard({
  name,
  type,
  priceRange,
  location,
  imageUrl,
  onClick,
  availableTimes,
  showPlaceholder,
}: RestaurantGridCardProps) {
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  const handleBookmarkClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsBookmarked(!isBookmarked);
  };

  return (
    <Card
      className="cursor-pointer hover:shadow-lg pt-0 pb-2 transition-all group overflow-hidden"
      onClick={onClick}
    >
      {/* Image */}
      <div className={cn(
        "relative aspect-4/3 w-full bg-muted overflow-hidden",
        !imageLoaded && imageUrl && "animate-pulse"
      )}>
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onLoad={() => setImageLoaded(true)}
            onError={(e) => {
              e.currentTarget.style.display = "none";
              setImageLoaded(true);
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            <MapPin className="size-12" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="px-4 pb-2 space-y-1">
        {/* Name and Price */}
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold text-base line-clamp-1 group-hover:text-primary transition-colors">
            {name}
          </h3>
          {priceRange > 0 && (
            <span className="text-sm text-muted-foreground font-medium shrink-0">
              {"$".repeat(priceRange)}
            </span>
          )}
        </div>

        {/* Type */}
        {type && type !== "N/A" && (
          <p className="text-sm text-muted-foreground line-clamp-1">{type}</p>
        )}

        {/* Location */}
        <div className="items-center flex flex-row justify-between">
          {location && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPin className="size-3.5 shrink-0" />
              <span className="line-clamp-1">{location}</span>
            </div>
          )}

          <Toggle
            pressed={isBookmarked}
            onPressedChange={setIsBookmarked}
            onClick={handleBookmarkClick}
            aria-label="Toggle bookmark"
            size="sm"
            variant="outline"
            className="bg-white/90 hover:bg-white data-[state=on]:bg-white data-[state=on]:*:[svg]:fill-primary data-[state=on]:*:[svg]:stroke-primary h-9 w-9 p-0"
          >
            <Bookmark className="size-4" />
          </Toggle>
        </div>

        {/* Reservation Times or Placeholder */}
        {showPlaceholder && (
          <div className="text-xs text-muted-foreground italic">
            {/* TODO: AI Summary */}
          </div>
        )}

        {availableTimes && availableTimes.length > 0 && (
          <div className="mt-2">
            <p className="text-xs text-muted-foreground mb-1">
              Available times:
            </p>
            <div className="flex flex-wrap gap-1">
              {availableTimes.slice(0, 4).map((time, index) => (
                <span
                  key={index}
                  className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-md font-medium"
                >
                  {time}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
