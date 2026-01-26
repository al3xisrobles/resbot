import { MapPin, Banknote, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { VenueData, VenueLinks } from "../lib/types";

interface VenueInfoProps {
  venueData: VenueData;
  venueLinks: VenueLinks | null;
  loadingLinks: boolean;
}

export function VenueInfo({ venueData, venueLinks, loadingLinks }: VenueInfoProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-start gap-3 justify-between">
        <div className="flex items-start gap-3 flex-1">
          <MapPin className="size-5 text-muted-foreground mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Address</p>
            {venueLinks?.googleMaps ? (
              <a
                href={venueLinks.googleMaps}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm hover:underline cursor-pointer"
              >
                {venueData.address}
              </a>
            ) : (
              <p className="text-sm text-muted-foreground">
                {venueData.address}
              </p>
            )}
            {venueData.neighborhood && (
              <p className="text-sm text-muted-foreground">
                {venueData.neighborhood}
              </p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className={`gap-2 ${loadingLinks ? "animate-pulse" : ""}`}
            disabled={!venueLinks?.googleMaps || loadingLinks}
            onClick={() => {
              if (venueLinks?.googleMaps) {
                window.open(venueLinks.googleMaps, "_blank");
              }
            }}
          >
            <ExternalLink className="size-4" />
            Google Maps
          </Button>
          <Button
            variant="outline"
            size="sm"
            className={`gap-2 ${loadingLinks ? "animate-pulse" : ""}`}
            disabled={!venueLinks?.resy || loadingLinks}
            onClick={() => {
              if (venueLinks?.resy) {
                window.open(venueLinks.resy, "_blank");
              }
            }}
          >
            <ExternalLink className="size-4" />
            Resy
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Banknote className="size-5 text-muted-foreground shrink-0" />
        <div>
          <p className="font-medium">Price Range</p>
          <p className="text-sm text-muted-foreground">
            {"$".repeat(venueData.price_range || 1)}
          </p>
        </div>
      </div>
    </div>
  );
}
