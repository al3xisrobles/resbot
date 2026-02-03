import { useState } from "react";
import { Bookmark, Share } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import type { VenueData } from "../lib/types";

/** Quick ease-out curve for micro-interactions */
const EASE_OUT_QUAD: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

interface VenueHeaderProps {
  venueData: VenueData;
}

export function VenueHeader({ venueData }: VenueHeaderProps) {
  const [isBookmarked, setIsBookmarked] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE_OUT_QUAD, delay: 0.05 }}
    >
      <div className="flex flex-row justify-between items-start">
        <h2 className="text-3xl font-bold">{venueData.name}</h2>
        <motion.div
          className="flex gap-2"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.25, ease: EASE_OUT_QUAD, delay: 0.15 }}
        >
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setIsBookmarked(!isBookmarked)}
          >
            <Bookmark
              className={`size-4 ${
                isBookmarked ? "fill-primary stroke-primary" : ""
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
        </motion.div>
      </div>
      <motion.div
        className="flex items-center gap-2 text-muted-foreground mt-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.25, ease: EASE_OUT_QUAD, delay: 0.2 }}
      >
        <span>{venueData.type}</span>
        {venueData.price_range && (
          <>
            <span className="text-muted-foreground/60">•</span>
            <span>{"$".repeat(venueData.price_range)}</span>
          </>
        )}
      </motion.div>
      {venueData.description && (
        <motion.p
          className="text-muted-foreground mt-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25, ease: EASE_OUT_QUAD, delay: 0.25 }}
        >
          {venueData.description}
        </motion.p>
      )}
    </motion.div>
  );
}
