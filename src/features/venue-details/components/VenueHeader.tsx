import { useState } from "react";
import { Bookmark, Share } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import type { VenueData } from "../lib/types";

interface VenueHeaderProps {
  venueData: VenueData;
}

export function VenueHeader({ venueData }: VenueHeaderProps) {
  const [isBookmarked, setIsBookmarked] = useState(false);

  return (
    <div>
      <div className="flex flex-row justify-between items-center">
        <h2 className="text-3xl font-bold">{venueData.name}</h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setIsBookmarked(!isBookmarked)}
          >
            <Bookmark
              className={`size-4 ${isBookmarked
                ? "fill-primary stroke-primary"
                : ""
                }`}
            />
            Bookmark
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => {
              const url = window.location.href;
              navigator.clipboard.writeText(url);
              toast("Link copied to clipboard", {
                description: "Share this restaurant with friends",
              });
            }}
          >
            <Share className="size-4" />
            Share
          </Button>
        </div>
      </div>
      <p className="text-muted-foreground mt-2">{venueData.type}</p>
      {venueData.description && (
        <p className="text-muted-foreground mt-2">{venueData.description}</p>
      )}
    </div>
  );
}
