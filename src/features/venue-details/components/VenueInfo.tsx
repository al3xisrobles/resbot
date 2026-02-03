import { MapPin, ExternalLink } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import type { VenueData, VenueLinks } from "../lib/types";

/** Quick ease-out curve for micro-interactions */
const EASE_OUT_QUAD: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

interface VenueInfoProps {
  venueData: VenueData;
  venueLinks: VenueLinks | null;
  loadingLinks: boolean;
}

export function VenueInfo({ venueData, venueLinks, loadingLinks }: VenueInfoProps) {
  return (
    <motion.div
      className="space-y-3"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE_OUT_QUAD, delay: 0.05 }}
    >
      <div className="flex items-start gap-3 justify-between">
        <motion.div
          className="flex items-start gap-3 flex-1"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.25, ease: EASE_OUT_QUAD, delay: 0.1 }}
        >
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
        </motion.div>
        <motion.div
          className="flex gap-2"
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.25, ease: EASE_OUT_QUAD, delay: 0.15 }}
        >
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
        </motion.div>
      </div>


    </motion.div>
  );
}
